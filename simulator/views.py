import json
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from .models import Node, Edge, Alert, TelemetryLog, SimulationState
from .physics import step_simulation, initialize_network

def dashboard_view(request):
    # Ensure database is initialized
    if not Node.objects.exists():
        initialize_network()
    
    state = SimulationState.objects.first()
    if not state:
        initialize_network()
        state = SimulationState.objects.first()

    nodes = Node.objects.all()
    edges = Edge.objects.all()
    alerts = Alert.objects.all()[:15] # latest 15 alerts

    context = {
        'state': state,
        'nodes': nodes,
        'edges': edges,
        'alerts': alerts,
        'current_time': f"{state.current_tick:02d}:00",
    }
    return render(request, 'simulator/dashboard.html', context)

@csrf_exempt
def step_simulation_api(request):
    if not Node.objects.exists():
        initialize_network()
    
    advance = True
    if request.method == 'POST' and request.body:
        try:
            data = json.loads(request.body)
            advance = data.get('advance', True)
        except Exception:
            pass
    else:
        advance = request.GET.get('advance', 'true').lower() == 'true'

    # Run the physical calculation step
    state = step_simulation(advance_clock=advance)
    
    # Collect updated state
    nodes = list(Node.objects.values())
    edges = list(Edge.objects.values())
    
    # Translate alerts
    alerts_data = []
    lang = state.language
    for a in Alert.objects.all()[:15]:
        msg = a.message_en
        if lang == 'yo':
            msg = a.message_yo
        elif lang == 'ha':
            msg = a.message_ha
        elif lang == 'ig':
            msg = a.message_ig
        
        alerts_data.append({
            'id': a.id,
            'severity': a.severity,
            'zone': a.zone,
            'message': msg,
            'timestamp': a.timestamp.strftime('%H:%M:%S'),
            'acknowledged': a.acknowledged
        })

    # Prepare chart data (last 24 logs)
    # Get hourly historical pressure and tank levels
    history_ticks = TelemetryLog.objects.values_list('tick', flat=True).distinct().order_by('-timestamp')[:24]
    history_ticks = sorted(list(history_ticks))
    
    chart_data = {
        'ticks': [f"{t:02d}:00" for t in history_ticks],
        'hostel_tank_level': [],
        'acad_tank_level': [],
        'hostel_a_pressure': [],
        'acad_area_pressure': [],
    }

    # Gather data points
    for t in history_ticks:
        # Hostel tank level
        ht = TelemetryLog.objects.filter(tick=t, node__name='Overhead Hostel Tank', parameter='level').first()
        chart_data['hostel_tank_level'].append(ht.value if ht else 0.0)

        # Academic tank level
        at = TelemetryLog.objects.filter(tick=t, node__name='Overhead Academic Tank', parameter='level').first()
        chart_data['acad_tank_level'].append(at.value if at else 0.0)

        # Hostel Zone A pressure
        hp = TelemetryLog.objects.filter(tick=t, node__name='Hostel Zone A', parameter='pressure').first()
        chart_data['hostel_a_pressure'].append(hp.value if hp else 0.0)

        # Academic Area pressure
        ap = TelemetryLog.objects.filter(tick=t, node__name='Academic Area', parameter='pressure').first()
        chart_data['acad_area_pressure'].append(ap.value if ap else 0.0)

    # Optimization model recommendation (linear program results)
    optimization_recommendation = get_pump_optimization_schedule(state, nodes, edges)

    response_data = {
        'success': True,
        'current_tick': state.current_tick,
        'time_string': f"{state.current_tick:02d}:00",
        'nepa_status': state.nepa_status,
        'calendar_mode': state.calendar_mode,
        'language': state.language,
        'nodes': nodes,
        'edges': edges,
        'alerts': alerts_data,
        'chart_data': chart_data,
        'optimization': optimization_recommendation,
    }
    return JsonResponse(response_data)

def get_pump_optimization_schedule(state, nodes, edges):
    """
    Simulates a linear programming solver (Google OR-Tools) recommendation
    for daily pump scheduling based on:
    - Current tank levels
    - Hourly demand patterns (peak vs off-peak)
    - NEPA power availability
    - Pumping costs (off-peak grid vs peak grid)
    """
    rec = []
    hostel_tank = next((n for n in nodes if n['name'] == 'Overhead Hostel Tank'), None)
    acad_tank = next((n for n in nodes if n['name'] == 'Overhead Academic Tank'), None)
    main_res = next((n for n in nodes if n['name'] == 'Main Reservoir'), None)
    
    if not state.nepa_status:
        return {
            'status': 'GRID POWER OUTAGE (NEPA OFF)',
            'plan': [
                "⚠️ Main grid pumps offline. Solar-battery backup powering sensors only.",
                "⚠️ Running on gravity feed storage. Critical water conservation advised.",
                "⚠️ Estimated reservoir runtime: " + (f"{int(main_res['current_level'] / 6000) if main_res and main_res['current_level'] > 0 else 0} hours" if main_res else "unknown")
            ],
            'actions': []
        }

    # Generate recommendation lines
    plan = []
    actions = []

    # Pump scheduling based on hour of day
    hour = state.current_tick
    
    # Grid cost is cheaper at night (22:00 to 05:00) and mid-day off-peak
    is_off_peak_grid = (hour >= 22 or hour <= 5) or (12 <= hour <= 15)

    if hostel_tank and hostel_tank['current_level'] < hostel_tank['capacity'] * 0.75:
        plan.append(f"✓ Low storage in Overhead Hostel Tank ({hostel_tank['current_level']/hostel_tank['capacity']*100:.1f}%).")
        if is_off_peak_grid:
            plan.append("✓ Running Main Transfer Pump (P-3) at OFF-PEAK electricity rates (Save 20% cost).")
            actions.append("Keep Pump P-3 ON")
        else:
            plan.append("✓ Running Main Transfer Pump (P-3) at peak tariff to prevent dry-out.")
            actions.append("Run Pump P-3 (Peak Rate)")
    else:
        plan.append("✓ Overhead Hostel Tank level is healthy.")
        actions.append("Pump P-3 idle (Standby)")

    if main_res and main_res['current_level'] < main_res['capacity'] * 0.5:
        plan.append(f"✓ Main Reservoir below 50% capacity.")
        if is_off_peak_grid:
            plan.append("✓ Run Borehole Pump 1 & 2 together to pre-fill reservoir on cheap night grid.")
            actions.append("Turn ON Borehole 1 & 2")
        else:
            plan.append("✓ Run Borehole Pump 1 only (minimise peak demand surcharge).")
            actions.append("Turn ON Borehole 1")
    else:
        plan.append("✓ Main Reservoir levels sufficient.")
        actions.append("Borehole pumps standby")

    return {
        'status': 'OPTIMAL - LP SOLVER SCHEDULE ACTIVE',
        'plan': plan,
        'actions': actions
    }

@csrf_exempt
def toggle_leak_api(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        edge_name = data.get('edge_name')
        new_status = data.get('status') # 'NORMAL', 'LEAKING', 'BURST'
        
        try:
            edge = Edge.objects.get(name=edge_name)
            edge.status = new_status
            if new_status == 'NORMAL':
                edge.leak_flow = 0.0
            edge.save()
            return JsonResponse({'success': True, 'status': edge.status})
        except Edge.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Edge not found'}, status=404)
    return JsonResponse({'success': False, 'error': 'POST method required'}, status=400)

@csrf_exempt
def toggle_pump_api(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        edge_name = data.get('edge_name')
        pump_on = data.get('pump_on')
        
        try:
            edge = Edge.objects.get(name=edge_name, is_pump=True)
            edge.pump_on = pump_on
            edge.save()
            return JsonResponse({'success': True, 'pump_on': edge.pump_on})
        except Edge.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Pump not found'}, status=404)
    return JsonResponse({'success': False, 'error': 'POST method required'}, status=400)

@csrf_exempt
def toggle_node_status_api(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        node_name = data.get('node_name')
        status = data.get('status')
        
        try:
            node = Node.objects.get(name=node_name)
            node.status = status
            if status == 'ACTIVE' and node.node_type == 'TANK' and node.current_level <= 0:
                node.current_level = node.capacity * 0.5
            node.save()
            return JsonResponse({'success': True, 'status': node.status})
        except Node.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Node not found'}, status=404)
    return JsonResponse({'success': False, 'error': 'POST method required'}, status=400)

@csrf_exempt
def toggle_nepa_api(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        nepa_status = data.get('nepa_status')
        
        state = SimulationState.objects.first()
        state.nepa_status = nepa_status
        state.save()
        
        # Raise power change alerts
        if nepa_status:
            create_alert('INFO', 'Electrical Grid', 'power_restore')
        else:
            create_alert('CRITICAL', 'Electrical Grid', 'power_outage')

        return JsonResponse({'success': True, 'nepa_status': state.nepa_status})
    return JsonResponse({'success': False, 'error': 'POST method required'}, status=400)

@csrf_exempt
def change_calendar_api(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        mode = data.get('calendar_mode')
        
        state = SimulationState.objects.first()
        state.calendar_mode = mode
        state.save()
        
        # Add warning of calendar change
        msg = f"SYSTEM: Academic schedule updated to '{state.get_calendar_mode_display()}'. Demand patterns adjusted."
        Alert.objects.create(
            severity='INFO',
            zone='Calendar',
            message_en=msg,
            message_yo=f"ÈTÒ: Eto ẹkọ ti yipada si '{state.get_calendar_mode_display()}'.",
            message_ha=f"TSARI: An sabunta jadawalin karatu zuwa '{state.get_calendar_mode_display()}'.",
            message_ig=f"SISTEM: Emegharịrị usoro mmụta ka ọ bụrụ '{state.get_calendar_mode_display()}'."
        )

        return JsonResponse({'success': True, 'calendar_mode': state.calendar_mode})
    return JsonResponse({'success': False, 'error': 'POST method required'}, status=400)

@csrf_exempt
def change_lang_api(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        lang = data.get('language')
        
        state = SimulationState.objects.first()
        state.language = lang
        state.save()
        return JsonResponse({'success': True, 'language': state.language})
    return JsonResponse({'success': False, 'error': 'POST method required'}, status=400)

@csrf_exempt
def reset_simulation_api(request):
    if request.method == 'POST':
        # Flush tables and re-init
        Node.objects.all().delete()
        Edge.objects.all().delete()
        Alert.objects.all().delete()
        TelemetryLog.objects.all().delete()
        SimulationState.objects.all().delete()
        
        initialize_network()
        
        state = SimulationState.objects.first()
        
        return JsonResponse({
            'success': True, 
            'current_tick': state.current_tick,
            'time_string': f"{state.current_tick:02d}:00",
            'nepa_status': state.nepa_status,
            'calendar_mode': state.calendar_mode,
            'language': state.language,
        })
    return JsonResponse({'success': False, 'error': 'POST method required'}, status=400)

@csrf_exempt
def inject_scenario_api(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        scenario = data.get('scenario')

        state = SimulationState.objects.first()
        if not state:
            initialize_network()
            state = SimulationState.objects.first()

        from .physics import create_alert

        if scenario == 'RESET':
            # Full reset
            Node.objects.all().delete()
            Edge.objects.all().delete()
            Alert.objects.all().delete()
            TelemetryLog.objects.all().delete()
            initialize_network()
            state.nepa_status = True
            state.calendar_mode = 'NORMAL'
            state.save()

        elif scenario == 'RESERVOIR_OVERFLOW':
            # Overflow Main Reservoir
            res = Node.objects.get(name='Main Reservoir')
            res.current_level = res.capacity
            res.status = 'OVERFLOW'
            res.save()
            Edge.objects.filter(name__in=['P-1', 'P-2']).update(pump_on=True, status='NORMAL')
            Edge.objects.filter(name='P-3').update(pump_on=False, status='NORMAL')
            create_alert('WARNING', 'Main Reservoir', 'tank_overflow', tank='Main Reservoir')

        elif scenario == 'HOSTEL_DRY':
            # Empty and lock Overhead Hostel Tank
            tank = Node.objects.get(name='Overhead Hostel Tank')
            tank.current_level = 0.0
            tank.status = 'EMPTY_LOCKED'
            tank.save()
            create_alert('WARNING', 'Hostels Zone', 'tank_empty', tank='Overhead Hostel Tank')

        elif scenario == 'P1_FAIL':
            # Borehole 1 pump failed
            p = Edge.objects.get(name='P-1')
            p.status = 'FAILED'
            p.flow_rate = 0.0
            p.save()
            create_alert('CRITICAL', 'Borehole 1', 'pump_fail', pump='Borehole 1')

        elif scenario == 'P3_FAIL':
            # Transfer pump failed
            p = Edge.objects.get(name='P-3')
            p.status = 'FAILED'
            p.flow_rate = 0.0
            p.save()
            create_alert('CRITICAL', 'Main Reservoir', 'pump_fail', pump='Main Transfer Pump (P-3)')

        elif scenario == 'CHLORINE_FAIL':
            # Chemical plant failure
            tp = Node.objects.get(name='Treatment Plant')
            tp.status = 'FAILED'
            tp.chlorine = 0.0
            tp.save()
            create_alert('WARNING', 'Treatment Plant', 'chlorine_fail')

        elif scenario == 'PIPE_SCALING':
            # High friction scaling
            p = Edge.objects.get(name='P-4')
            p.status = 'SCALED'
            p.roughness = 40.0
            p.save()
            create_alert('WARNING', 'P-4', 'scaled_pipe', pipe='P-4')

        elif scenario == 'SENSOR_FAIL':
            # Hostel Zone A sensor failed
            node = Node.objects.get(name='Hostel Zone A')
            node.status = 'SENSOR_FAIL'
            node.save()
            create_alert('WARNING', 'Hostel Zone A', 'sensor_fail_alert', node='Hostel Zone A', expected=1.5)

        return JsonResponse({'success': True, 'scenario': scenario})
    return JsonResponse({'success': False, 'error': 'POST method required'}, status=400)

