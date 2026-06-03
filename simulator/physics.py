import math
import random
from django.utils import timezone
from .models import Node, Edge, Alert, TelemetryLog, SimulationState

# Translation dictionary for Yoruba, Hausa, and Igbo
TRANSLATIONS = {
    'leak_warning': {
        'en': "WARNING: Flow imbalance of {pct:.1f}% detected in {zone}. Possible leak in pipeline {pipe}.",
        'yo': "ÌKÌLỌ̀: Ìyàtọ̀ sísàn omi ti {pct:.1f}% ní {zone}. O ṣeé ṣe kí jòjò wà nínú páìpù {pipe}.",
        'ha': "GARGADI: An sami rashin daidaituwar kwarara da kashi {pct:.1f}% a {zone}. Kwatami yoyo a bututu {pipe}.",
        'ig': "NDỌ AKA NA NTỊ: Ọdịiche nrụgide nke {pct:.1f}% na {zone}. O nwere ike ịbụ na paịpụ {pipe} na-agbapụta mmiri.",
    },
    'burst_critical': {
        'en': "CRITICAL: Severe pressure drop and flow surge in {zone}. Pipe burst confirmed in {pipe}!",
        'yo': "KÒ KÒ RẸ̀: Ọ̀gọ̀ọ̀rọ̀ omi tó ń jáde àti ìṣubú pípé ní {zone}. Páìpù {pipe} ti sán!",
        'ha': "MAHIMMI: Rage matsin lamba da sauri da kwarara a {zone}. Bututu {pipe} ya fashe!",
        'ig': "NDỌ AKA NA NTỊ DỊ EGWI: Ọdịda nrụgide siri ike na {zone}. Paịpụ {pipe} agbawaala!",
    },
    'acoustic_alert': {
        'en': "ANOMALY: High-frequency acoustic vibration ({freq} Hz) detected on {pipe} indicating active leak.",
        'yo': "ÀMÌ ÌBÀJẸ́: Gbigbọn ohun pípé ga ({freq} Hz) lórí {pipe} tí ń tọ́ka sí jòjò omi.",
        'ha': "ALAMAR MATSALA: Karar girgiza mai karfi ({freq} Hz) a {pipe} wanda ke nuna yoyon ruwa.",
        'ig': "IHE ANỌMALỊ: Ụda jijiji dị elu ({freq} Hz) na {pipe} na-egosi mmiri na-agbapụta.",
    },
    'tank_overflow': {
        'en': "ALERT: Storage tank {tank} is overflowing! Inflow exceeds storage capacity.",
        'yo': "ÌWÀ RẸ̀: Agbada omi {tank} ti kún àkúnwọ́sílẹ̀! Omi tó ń wọ̀ ju agbára rẹ̀ lọ.",
        'ha': "GARGADI: Tanki {tank} yana zuba! Ruwan da ke shiga ya fi karfinsa.",
        'ig': "NDỌ AKA NA NTỊ: Tankị {tank} na-ejupụta na-awụfu! Mmiri na-aba na ya karịrị ike ya.",
    },
    'tank_empty': {
        'en': "WARNING: Storage tank {tank} is dry! Downstream nodes have lost water supply.",
        'yo': "ÌKÌLỌ̀: Agbada omi {tank} ti gbẹ patapata! Awọn agbegbe isalẹ ti padanu omi.",
        'ha': "GARGADI: Tanki {tank} ya bushe! Layukan kasa sun rasa ruwa.",
        'ig': "NDỌ AKA NA NTỊ: Tankị {tank} agbawaala ncha! Ndị nọ n'okpuru enweghị mmiri.",
    },
    'power_outage': {
        'en': "SYSTEM: Main grid power outage. Switched to solar/battery backup. Borehole pumps offline.",
        'yo': "ÈTÒ: Iná kúrò lórí ila. A ti yí padà sí iná oòrùn/bátirì. Àwọn pọ́mpù borehole kò ṣiṣẹ́.",
        'ha': "TSARI: Wutar lantarki ta dauke. An koma wutar rana/bateri. Pam-pam na rijiya ba sa aiki.",
        'ig': "SISTEM: Ọkụ eletrik agbanyụọla. Ejila wuta anyanwụ na batrị. Pọmpụ olulu mmiri anọghị n'ịntanetị.",
    },
    'power_restore': {
        'en': "SYSTEM: Grid power restored. Normal pumping schedules resumed.",
        'yo': "ÈTÒ: Iná ila ti padà. Pọ́mpù omi ti bẹ̀rẹ̀ iṣẹ́ padà.",
        'ha': "TSARI: Wutar lantarki ta dawo. Pam-pam sun dawo aiki kamar da.",
        'ig': "SISTEM: Ọkụ eletrik alọghachila. Pọmpụ mmiri amalitela ọrụ ọzọ.",
    },
    'pump_fail': {
        'en': "ALERT: Mechanical failure detected in pump {pump}! Flow output is zero.",
        'yo': "ÌKÌLỌ̀: Kùnà ẹrọ lórí pọ́mpù {pump}! Sísàn omi jẹ́ odo.",
        'ha': "GARGADI: Lalacewar inji a famfo {pump}! Kwararar ruwa ya zama sifiri.",
        'ig': "NDỌ AKA NA NTỊ: Ọdịda igwe na pọmpụ {pump}! Mmiri anaghị agba.",
    },
    'chlorine_fail': {
        'en': "WARNING: Chlorine dosing system failure at Treatment Plant. Residual chlorine dropping.",
        'yo': "ÌKÌLỌ̀: Ẹ̀rọ abẹ́rẹ́ chlorine kùnà ní Ilé Ìtọ́jú. Chlorine ń dín kù.",
        'ha': "GARGADI: Matsala a tsarin chlorine a Wurin Tace Ruwa. Sinadarin chlorine yana raguwa.",
        'ig': "NDỌ AKA NA NTỊ: Ọdịda sistemụ chlorine na Wurin Ọgwụgwọ. Chlorine na-ebelata.",
    },
    'scaled_pipe': {
        'en': "ANOMALY: High friction loss / internal scaling detected in pipe {pipe}. Downstream pressure degraded.",
        'yo': "ÀMÌ ÌBÀJẸ́: Ìṣòro dídín kù omi nínú páìpù {pipe}. Ida omi ti dín kù lẹ́yìn rẹ̀.",
        'ha': "ALAMAR MATSALA: Ragewar matsin lamba a bututu {pipe} saboda toshewa.",
        'ig': "IHE ANỌMALỊ: Nsogbu friction na paịpụ {pipe}. Nrụgide mmiri ebelatala.",
    },
    'sensor_fail_alert': {
        'en': "SENSOR FAULT: Node {node} reporting 0.0 bar, but Digital Twin model predicts {expected:.2f} bar. Physical sensor calibration required.",
        'yo': "ÀMÌ KỌ̀MPÚTÀ: Node {node} ń sọ pé 0.0 bar, ṣùgbọ́n Digital Twin sọ pé ó yẹ kó jẹ́ {expected:.2f} bar.",
        'ha': "MATSALA SENSOR: Na'urar node {node} tana nuna 0.0 bar, amma Digital Twin ya ce ya kamata ya zama {expected:.2f} bar.",
        'ig': "ỌDỊDA SENSOR: Sensor {node} na-egosi 0.0 bar, mana Digital Twin na-egosi na ọ ga-abụ {expected:.2f} bar.",
    }
}

def create_alert(severity, zone, alert_key, **kwargs):
    messages = {}
    for lang in ['en', 'yo', 'ha', 'ig']:
        template = TRANSLATIONS[alert_key][lang]
        messages[lang] = template.format(**kwargs)

    Alert.objects.create(
        severity=severity,
        zone=zone,
        message_en=messages['en'],
        message_yo=messages['yo'],
        message_ha=messages['ha'],
        message_ig=messages['ig']
    )

def initialize_network():
    # Ensure simulation state exists
    state, created = SimulationState.objects.get_or_create(id=1)
    if created:
        state.current_tick = 8  # Start at 8:00 AM
        state.nepa_status = True
        state.calendar_mode = 'NORMAL'
        state.language = 'en'
        state.save()

    # Core Nodes
    nodes_data = [
        # Pumps/Sources
        {'name': 'Borehole 1', 'node_type': 'PUMP', 'elevation': 0.0, 'pressure': 4.5, 'chlorine': 0.0, 'status': 'ACTIVE'},
        {'name': 'Borehole 2', 'node_type': 'PUMP', 'elevation': 2.0, 'pressure': 4.0, 'chlorine': 0.0, 'status': 'ACTIVE'},
        # Tanks
        {'name': 'Main Reservoir', 'node_type': 'TANK', 'elevation': 5.0, 'capacity': 500000.0, 'current_level': 350000.0, 'pressure': 0.5, 'chlorine': 0.2, 'status': 'ACTIVE'},
        {'name': 'Overhead Hostel Tank', 'node_type': 'TANK', 'elevation': 22.0, 'capacity': 100000.0, 'current_level': 75000.0, 'pressure': 1.2, 'chlorine': 1.5, 'status': 'ACTIVE'},
        {'name': 'Overhead Academic Tank', 'node_type': 'TANK', 'elevation': 18.0, 'capacity': 50000.0, 'current_level': 35000.0, 'pressure': 0.9, 'chlorine': 1.4, 'status': 'ACTIVE'},
        # Treatment
        {'name': 'Treatment Plant', 'node_type': 'JUNCTION', 'elevation': 6.0, 'pressure': 2.8, 'chlorine': 2.0, 'status': 'ACTIVE'},
        # Consumers
        {'name': 'Hostel Zone A', 'node_type': 'CONSUMER', 'elevation': 4.0, 'base_demand': 120.0, 'pressure': 1.8, 'chlorine': 1.2, 'status': 'ACTIVE'},
        {'name': 'Hostel Zone B', 'node_type': 'CONSUMER', 'elevation': 5.0, 'base_demand': 150.0, 'pressure': 1.7, 'chlorine': 1.1, 'status': 'ACTIVE'},
        {'name': 'Academic Area', 'node_type': 'CONSUMER', 'elevation': 8.0, 'base_demand': 60.0, 'pressure': 1.0, 'chlorine': 1.1, 'status': 'ACTIVE'},
        {'name': 'Medical Center', 'node_type': 'CONSUMER', 'elevation': 7.0, 'base_demand': 20.0, 'pressure': 1.1, 'chlorine': 1.3, 'status': 'ACTIVE'},
    ]

    nodes = {}
    for nd in nodes_data:
        node, created = Node.objects.get_or_create(name=nd['name'], defaults=nd)
        nodes[nd['name']] = node

    # Core Edges (Pipes & Pumps)
    # Hazen-Williams roughness: GI = 120, uPVC = 140, HDPE = 150
    edges_data = [
        {'name': 'P-1', 'source': nodes['Borehole 1'], 'target': nodes['Main Reservoir'], 'material': 'GI', 'diameter': 100.0, 'length': 150.0, 'roughness': 120.0, 'is_pump': True, 'pump_on': True},
        {'name': 'P-2', 'source': nodes['Borehole 2'], 'target': nodes['Main Reservoir'], 'material': 'GI', 'diameter': 100.0, 'length': 200.0, 'roughness': 120.0, 'is_pump': True, 'pump_on': False},
        {'name': 'P-3', 'source': nodes['Main Reservoir'], 'target': nodes['Treatment Plant'], 'material': 'GI', 'diameter': 150.0, 'length': 50.0, 'roughness': 120.0, 'is_pump': True, 'pump_on': True},
        {'name': 'P-4', 'source': nodes['Treatment Plant'], 'target': nodes['Overhead Hostel Tank'], 'material': 'uPVC', 'diameter': 100.0, 'length': 400.0, 'roughness': 140.0},
        {'name': 'P-5', 'source': nodes['Treatment Plant'], 'target': nodes['Overhead Academic Tank'], 'material': 'uPVC', 'diameter': 80.0, 'length': 300.0, 'roughness': 140.0},
        {'name': 'P-6', 'source': nodes['Overhead Hostel Tank'], 'target': nodes['Hostel Zone A'], 'material': 'uPVC', 'diameter': 75.0, 'length': 120.0, 'roughness': 140.0},
        {'name': 'P-7', 'source': nodes['Overhead Hostel Tank'], 'target': nodes['Hostel Zone B'], 'material': 'uPVC', 'diameter': 75.0, 'length': 180.0, 'roughness': 140.0},
        {'name': 'P-8', 'source': nodes['Overhead Academic Tank'], 'target': nodes['Academic Area'], 'material': 'uPVC', 'diameter': 50.0, 'length': 100.0, 'roughness': 140.0},
        {'name': 'P-9', 'source': nodes['Overhead Academic Tank'], 'target': nodes['Medical Center'], 'material': 'HDPE', 'diameter': 50.0, 'length': 150.0, 'roughness': 150.0},
    ]

    for ed in edges_data:
        Edge.objects.get_or_create(name=ed['name'], defaults=ed)

def get_demand_factor(hour, mode):
    # Base factors by hour of day
    if 6 <= hour <= 9:  # Morning peak
        hostel_factor = 2.5
        academic_factor = 0.5
    elif 10 <= hour <= 16:  # Lecture hours
        hostel_factor = 0.8
        academic_factor = 2.0
    elif 17 <= hour <= 21:  # Evening hostel return
        hostel_factor = 2.2
        academic_factor = 0.6
    else:  # Night
        hostel_factor = 0.3
        academic_factor = 0.1

    # Calendar modifications
    if mode == 'ASUU_STRIKE':
        hostel_factor *= 0.1
        academic_factor = 0.0
    elif mode == 'EXAMS':
        hostel_factor *= 1.2
        academic_factor *= 1.5
    elif mode == 'HOLIDAYS':
        hostel_factor *= 0.05
        academic_factor *= 0.1

    return hostel_factor, academic_factor

def calculate_friction_loss(flow_L_min, length, diameter_mm, roughness_c):
    if flow_L_min <= 0:
        return 0.0
    # Hazen-Williams formula in metric units:
    # h_f = 10.67 * L * Q^1.852 / (C^1.852 * D^4.87)
    Q_m3_s = (flow_L_min / 1000.0) / 60.0
    D_m = diameter_mm / 1000.0
    
    try:
        head_loss = 10.67 * length * (Q_m3_s ** 1.852) / ((roughness_c ** 1.852) * (D_m ** 4.87))
        return head_loss
    except ZeroDivisionError:
        return 999.0

def step_simulation(advance_clock=True):
    state = SimulationState.objects.get(id=1)
    
    if advance_clock:
        # 1. Advance Time Tick (1 hour per tick)
        state.current_tick = (state.current_tick + 1) % 24
        state.save()
    
    hour = state.current_tick
    hostel_f, acad_f = get_demand_factor(hour, state.calendar_mode)

    # Reload nodes and edges from db
    nodes = {n.name: n for n in Node.objects.all()}
    edges = {e.name: e for e in Edge.objects.all()}

    # Store old pressures for transient analysis
    old_pressures = {n.name: n.pressure for n in nodes.values()}

    # 2. Reset or adjust roughness for Scaled pipelines
    for e in edges.values():
        if e.status == 'SCALED':
            e.roughness = 40.0
            # Raise scaling alert if not already active
            if not Alert.objects.filter(severity='WARNING', zone=e.name).exists():
                create_alert('WARNING', e.name, 'scaled_pipe', pipe=e.name)
        elif e.status == 'NORMAL':
            # Reset to normal based on material
            e.roughness = 120.0 if e.material == 'GI' else (150.0 if e.material == 'HDPE' else 140.0)
        e.save()

    # 3. Update Consumer Demands (unless node status is SENSOR_FAIL, we calculate actual demands)
    nodes['Hostel Zone A'].current_demand = nodes['Hostel Zone A'].base_demand * hostel_f
    nodes['Hostel Zone B'].current_demand = nodes['Hostel Zone B'].base_demand * hostel_f
    nodes['Academic Area'].current_demand = nodes['Academic Area'].base_demand * acad_f
    nodes['Medical Center'].current_demand = nodes['Medical Center'].base_demand * 1.0  # Constant high-priority demand

    for name in ['Hostel Zone A', 'Hostel Zone B', 'Academic Area', 'Medical Center']:
        nodes[name].save()

    # 4. Simulate Leak Flows
    for e in edges.values():
        if e.status == 'LEAKING':
            e.leak_flow = 15.0 + random.uniform(-2, 2)
        elif e.status == 'BURST':
            e.leak_flow = 110.0 + random.uniform(-10, 10)
        else:
            e.leak_flow = 0.0
        e.save()

    # 5. Calculate pump flows (taking mechanical FAILED status into account)
    # Check Borehole 1 pump mechanical failure
    if edges['P-1'].status == 'FAILED':
        bh1_flow = 0.0
        if not Alert.objects.filter(severity='CRITICAL', zone='Borehole 1').exists():
            create_alert('CRITICAL', 'Borehole 1', 'pump_fail', pump='Borehole 1')
    else:
        bh1_flow = 180.0 if (edges['P-1'].pump_on and state.nepa_status) else 0.0
    
    # Check Borehole 2 pump mechanical failure
    if edges['P-2'].status == 'FAILED':
        bh2_flow = 0.0
        if not Alert.objects.filter(severity='CRITICAL', zone='Borehole 2').exists():
            create_alert('CRITICAL', 'Borehole 2', 'pump_fail', pump='Borehole 2')
    else:
        bh2_flow = 150.0 if (edges['P-2'].pump_on and state.nepa_status) else 0.0

    edges['P-1'].flow_rate = bh1_flow
    edges['P-2'].flow_rate = bh2_flow

    # Process Control: Main Transfer Pump P-3
    overhead_hostel_pct = (nodes['Overhead Hostel Tank'].current_level / nodes['Overhead Hostel Tank'].capacity) * 100.0
    overhead_acad_pct = (nodes['Overhead Academic Tank'].current_level / nodes['Overhead Academic Tank'].capacity) * 100.0

    transfer_pump = edges['P-3']
    if state.nepa_status and transfer_pump.status != 'FAILED':
        if overhead_hostel_pct < 70.0 or overhead_acad_pct < 70.0:
            transfer_pump.pump_on = True
        elif overhead_hostel_pct > 95.0 and overhead_acad_pct > 95.0:
            transfer_pump.pump_on = False
    else:
        transfer_pump.pump_on = False
    
    transfer_pump.save()

    main_res_level = nodes['Main Reservoir'].current_level
    
    if transfer_pump.status == 'FAILED':
        transfer_flow = 0.0
        if not Alert.objects.filter(severity='CRITICAL', zone='Main Reservoir').exists():
            create_alert('CRITICAL', 'Main Reservoir', 'pump_fail', pump='Main Transfer Pump (P-3)')
    else:
        transfer_flow = 300.0 if (transfer_pump.pump_on and main_res_level > 1000) else 0.0

    edges['P-3'].flow_rate = transfer_flow

    # Flow rates splitting to tanks
    if transfer_flow > 0:
        edges['P-4'].flow_rate = transfer_flow * 0.60 + edges['P-4'].leak_flow
        edges['P-5'].flow_rate = transfer_flow * 0.40 + edges['P-5'].leak_flow
    else:
        edges['P-4'].flow_rate = edges['P-4'].leak_flow
        edges['P-5'].flow_rate = edges['P-5'].leak_flow

    # Flow rates from gravity tanks to consumers
    edges['P-6'].flow_rate = nodes['Hostel Zone A'].current_demand + edges['P-6'].leak_flow
    edges['P-7'].flow_rate = nodes['Hostel Zone B'].current_demand + edges['P-7'].leak_flow
    edges['P-8'].flow_rate = nodes['Academic Area'].current_demand + edges['P-8'].leak_flow
    edges['P-9'].flow_rate = nodes['Medical Center'].current_demand + edges['P-9'].leak_flow

    for e in edges.values():
        e.save()

    # 6. Update Tank Volumes (1-hour integration)
    # Main Reservoir
    net_reservoir_flow = (bh1_flow + bh2_flow) - transfer_flow
    if advance_clock:
        nodes['Main Reservoir'].current_level = max(0.0, min(
            nodes['Main Reservoir'].capacity,
            nodes['Main Reservoir'].current_level + (net_reservoir_flow * 60.0)
        ))
    
    # Only auto-set tank status if not already set by scenario injection
    res_status_before = Node.objects.get(name='Main Reservoir').status
    if nodes['Main Reservoir'].current_level >= nodes['Main Reservoir'].capacity:
        nodes['Main Reservoir'].status = 'OVERFLOW'
        if not Alert.objects.filter(severity='WARNING', zone='Main Reservoir', message_en__contains='overflow').exists():
            create_alert('WARNING', 'Main Reservoir', 'tank_overflow', tank='Main Reservoir')
    elif nodes['Main Reservoir'].current_level <= 0:
        nodes['Main Reservoir'].status = 'EMPTY'
        if not Alert.objects.filter(severity='WARNING', zone='Main Reservoir', message_en__contains='dry').exists():
            create_alert('WARNING', 'Main Reservoir', 'tank_empty', tank='Main Reservoir')
    elif res_status_before not in ('OVERFLOW', 'EMPTY', 'EMPTY_LOCKED', 'FAILED', 'SENSOR_FAIL'):
        nodes['Main Reservoir'].status = 'ACTIVE'

    # Overhead Hostel Tank
    hostel_in = edges['P-4'].flow_rate - edges['P-4'].leak_flow
    hostel_out = edges['P-6'].flow_rate + edges['P-7'].flow_rate
    net_hostel_flow = hostel_in - hostel_out
    
    hostel_status_before = Node.objects.get(name='Overhead Hostel Tank').status
    if nodes['Overhead Hostel Tank'].status == 'EMPTY_LOCKED' or (nodes['Overhead Hostel Tank'].current_level <= 0 and net_hostel_flow < 0):
        # Force empty simulation state
        nodes['Overhead Hostel Tank'].current_level = 0.0
        nodes['Overhead Hostel Tank'].status = 'EMPTY'
        edges['P-6'].flow_rate = 0.0
        edges['P-7'].flow_rate = 0.0
        nodes['Hostel Zone A'].current_demand = 0.0
        nodes['Hostel Zone B'].current_demand = 0.0
    else:
        if advance_clock:
            nodes['Overhead Hostel Tank'].current_level = max(0.0, min(
                nodes['Overhead Hostel Tank'].capacity,
                nodes['Overhead Hostel Tank'].current_level + (net_hostel_flow * 60.0)
            ))
        if nodes['Overhead Hostel Tank'].current_level >= nodes['Overhead Hostel Tank'].capacity:
            nodes['Overhead Hostel Tank'].status = 'OVERFLOW'
            if not Alert.objects.filter(severity='WARNING', zone='Hostels Zone', message_en__contains='overflow').exists():
                create_alert('WARNING', 'Hostels Zone', 'tank_overflow', tank='Overhead Hostel Tank')
        elif nodes['Overhead Hostel Tank'].current_level <= 0:
            nodes['Overhead Hostel Tank'].status = 'EMPTY'
            if not Alert.objects.filter(severity='WARNING', zone='Hostels Zone', message_en__contains='dry').exists():
                create_alert('WARNING', 'Hostels Zone', 'tank_empty', tank='Overhead Hostel Tank')
        elif hostel_status_before not in ('OVERFLOW', 'EMPTY', 'EMPTY_LOCKED', 'FAILED', 'SENSOR_FAIL'):
            nodes['Overhead Hostel Tank'].status = 'ACTIVE'

    # Overhead Academic Tank
    acad_in = edges['P-5'].flow_rate - edges['P-5'].leak_flow
    acad_out = edges['P-8'].flow_rate + edges['P-9'].flow_rate
    net_acad_flow = acad_in - acad_out

    acad_status_before = Node.objects.get(name='Overhead Academic Tank').status
    if nodes['Overhead Academic Tank'].status == 'EMPTY_LOCKED' or (nodes['Overhead Academic Tank'].current_level <= 0 and net_acad_flow < 0):
        nodes['Overhead Academic Tank'].current_level = 0.0
        nodes['Overhead Academic Tank'].status = 'EMPTY'
        edges['P-8'].flow_rate = 0.0
        edges['P-9'].flow_rate = 0.0
        nodes['Academic Area'].current_demand = 0.0
        nodes['Medical Center'].current_demand = 0.0
    else:
        if advance_clock:
            nodes['Overhead Academic Tank'].current_level = max(0.0, min(
                nodes['Overhead Academic Tank'].capacity,
                nodes['Overhead Academic Tank'].current_level + (net_acad_flow * 60.0)
            ))
        if nodes['Overhead Academic Tank'].current_level >= nodes['Overhead Academic Tank'].capacity:
            nodes['Overhead Academic Tank'].status = 'OVERFLOW'
            if not Alert.objects.filter(severity='WARNING', zone='Academic Zone', message_en__contains='overflow').exists():
                create_alert('WARNING', 'Academic Zone', 'tank_overflow', tank='Overhead Academic Tank')
        elif nodes['Overhead Academic Tank'].current_level <= 0:
            nodes['Overhead Academic Tank'].status = 'EMPTY'
            if not Alert.objects.filter(severity='WARNING', zone='Academic Zone', message_en__contains='dry').exists():
                create_alert('WARNING', 'Academic Zone', 'tank_empty', tank='Overhead Academic Tank')
        elif acad_status_before not in ('OVERFLOW', 'EMPTY', 'EMPTY_LOCKED', 'FAILED', 'SENSOR_FAIL'):
            nodes['Overhead Academic Tank'].status = 'ACTIVE'

    # Save edges again with updated flows
    for e in edges.values():
        e.save()

    # 7. Chlorine Dosing System Failure
    if nodes['Treatment Plant'].status == 'FAILED':
        nodes['Treatment Plant'].chlorine = 0.0
        if not Alert.objects.filter(severity='WARNING', zone='Treatment Plant', message_en__contains='dosing').exists():
            create_alert('WARNING', 'Treatment Plant', 'chlorine_fail')
    else:
        nodes['Treatment Plant'].chlorine = 2.0
    nodes['Treatment Plant'].save()

    # 8. Calculate Node Pressures
    nodes['Main Reservoir'].pressure = 0.1 + (nodes['Main Reservoir'].current_level / nodes['Main Reservoir'].capacity) * 0.4
    
    # Treatment plant pressure (fed by transfer pump P-3)
    if transfer_flow > 0:
        head_loss_p3 = calculate_friction_loss(transfer_flow, edges['P-3'].length, edges['P-3'].diameter, edges['P-3'].roughness)
        nodes['Treatment Plant'].pressure = max(0.2, (nodes['Main Reservoir'].pressure * 10.0 + 35.0 - head_loss_p3 - (nodes['Treatment Plant'].elevation - nodes['Main Reservoir'].elevation)) / 10.0)
    else:
        nodes['Treatment Plant'].pressure = 0.1
    nodes['Treatment Plant'].save()

    # Consumers fed from Overhead Hostel Tank
    hostel_tank = nodes['Overhead Hostel Tank']
    hostel_head = (hostel_tank.elevation - 5.0) if hostel_tank.status != 'EMPTY' else 0.0
    
    # Hostel Zone A
    loss_p6 = calculate_friction_loss(edges['P-6'].flow_rate, edges['P-6'].length, edges['P-6'].diameter, edges['P-6'].roughness)
    nodes['Hostel Zone A'].pressure = max(0.0, (hostel_head - (nodes['Hostel Zone A'].elevation - hostel_tank.elevation) - loss_p6) / 10.0)
    
    # Hostel Zone B
    loss_p7 = calculate_friction_loss(edges['P-7'].flow_rate, edges['P-7'].length, edges['P-7'].diameter, edges['P-7'].roughness)
    nodes['Hostel Zone B'].pressure = max(0.0, (hostel_head - (nodes['Hostel Zone B'].elevation - hostel_tank.elevation) - loss_p7) / 10.0)

    # Consumers fed from Overhead Academic Tank
    acad_tank = nodes['Overhead Academic Tank']
    acad_head = (acad_tank.elevation - 5.0) if acad_tank.status != 'EMPTY' else 0.0

    # Academic Area
    loss_p8 = calculate_friction_loss(edges['P-8'].flow_rate, edges['P-8'].length, edges['P-8'].diameter, edges['P-8'].roughness)
    nodes['Academic Area'].pressure = max(0.0, (acad_head - (nodes['Academic Area'].elevation - acad_tank.elevation) - loss_p8) / 10.0)

    # Medical Center
    loss_p9 = calculate_friction_loss(edges['P-9'].flow_rate, edges['P-9'].length, edges['P-9'].diameter, edges['P-9'].roughness)
    nodes['Medical Center'].pressure = max(0.0, (acad_head - (nodes['Medical Center'].elevation - acad_tank.elevation) - loss_p9) / 10.0)

    # Apply SENSOR FAULT overrides
    # Physical sensor fails and reports 0.0 bar, while model expects higher
    for consumer_name in ['Hostel Zone A', 'Hostel Zone B', 'Academic Area', 'Medical Center']:
        n = nodes[consumer_name]
        if n.status == 'SENSOR_FAIL':
            model_estimated_pressure = n.pressure  # save model prediction
            n.pressure = 0.0  # physical sensor reading is broken (reports 0)
            n.save()
            
            # Anomaly alert: mismatch between sensor and model
            if model_estimated_pressure > 0.4:
                if not Alert.objects.filter(severity='WARNING', zone=n.name, message_en__contains='SENSOR FAULT').exists():
                    create_alert('WARNING', n.name, 'sensor_fail_alert', node=n.name, expected=model_estimated_pressure)
        else:
            n.save()

    # 9. Simulate Chlorine Concentrations & Mixing Decay
    # Mixing decay in Overhead Tanks
    for tank_name, inflow_pipe, source_node in [('Overhead Hostel Tank', 'P-4', 'Treatment Plant'), ('Overhead Academic Tank', 'P-5', 'Treatment Plant')]:
        tank = nodes[tank_name]
        inflow = edges[inflow_pipe].flow_rate
        cl_in = nodes[source_node].chlorine
        k_decay = 0.04
        old_chlorine_decayed = tank.chlorine * math.exp(-k_decay)
        
        if tank.current_level > 0:
            tank.chlorine = ((tank.current_level - inflow * 60.0) * old_chlorine_decayed + (inflow * 60.0 * cl_in)) / tank.current_level
            tank.chlorine = max(0.0, min(2.0, tank.chlorine))
        else:
            tank.chlorine = 0.0
        tank.save()

    # Pipeline chlorine travel decay
    # Hostel Zone A
    vel_p6 = edges['P-6'].flow_rate / (math.pi * ((edges['P-6'].diameter/2000.0)**2) * 1000.0) if edges['P-6'].flow_rate > 0 else 0
    res_time_p6 = (edges['P-6'].length / vel_p6) / 3600.0 if vel_p6 > 0 else 24.0
    nodes['Hostel Zone A'].chlorine = max(0.0, nodes['Overhead Hostel Tank'].chlorine * math.exp(-0.15 * res_time_p6))

    # Hostel Zone B
    vel_p7 = edges['P-7'].flow_rate / (math.pi * ((edges['P-7'].diameter/2000.0)**2) * 1000.0) if edges['P-7'].flow_rate > 0 else 0
    res_time_p7 = (edges['P-7'].length / vel_p7) / 3600.0 if vel_p7 > 0 else 24.0
    nodes['Hostel Zone B'].chlorine = max(0.0, nodes['Overhead Hostel Tank'].chlorine * math.exp(-0.15 * res_time_p7))

    # Academic Area
    vel_p8 = edges['P-8'].flow_rate / (math.pi * ((edges['P-8'].diameter/2000.0)**2) * 1000.0) if edges['P-8'].flow_rate > 0 else 0
    res_time_p8 = (edges['P-8'].length / vel_p8) / 3600.0 if vel_p8 > 0 else 24.0
    nodes['Academic Area'].chlorine = max(0.0, nodes['Overhead Academic Tank'].chlorine * math.exp(-0.15 * res_time_p8))

    # Medical Center
    vel_p9 = edges['P-9'].flow_rate / (math.pi * ((edges['P-9'].diameter/2000.0)**2) * 1000.0) if edges['P-9'].flow_rate > 0 else 0
    res_time_p9 = (edges['P-9'].length / vel_p9) / 3600.0 if vel_p9 > 0 else 24.0
    nodes['Medical Center'].chlorine = max(0.0, nodes['Overhead Academic Tank'].chlorine * math.exp(-0.15 * res_time_p9))

    for n in nodes.values():
        n.save()

    # 10. Update failure probabilities
    for e in edges.values():
        if e.status in ['LEAKING', 'BURST', 'FAILED']:
            e.failure_probability = min(100.0, e.failure_probability + 2.0)
        else:
            fatigue = 0.05
            if e.is_pump and e.pump_on:
                fatigue += 0.1
            if e.flow_rate > 150.0:
                fatigue += 0.2
            e.failure_probability = min(99.0, e.failure_probability + fatigue)
        e.save()

    # 11. Anomaly Detection and Warnings (Digital Twin Real-time Observer)
    # Layer 1: Acoustic Screening
    for e in edges.values():
        if e.status in ['LEAKING', 'BURST']:
            freq = int(820 + 200 * random.random()) if e.status == 'LEAKING' else int(450 + 100 * random.random())
            if not Alert.objects.filter(severity='WARNING', zone=e.name, message_en__contains='acoustic').exists():
                create_alert('WARNING', e.name, 'acoustic_alert', pipe=e.name, freq=freq)

    # Layer 2: District Metered Area (DMA) Mass Balance
    # Zone 1: Hostel Distribution
    zone1_in = edges['P-4'].flow_rate
    zone1_out = edges['P-6'].flow_rate + edges['P-7'].flow_rate
    if zone1_in > 0:
        imbalance1 = (abs(zone1_in - zone1_out) / zone1_in) * 100.0
        if imbalance1 > 3.0:
            active_leak = 'P-4' if edges['P-4'].status != 'NORMAL' else ('P-6' if edges['P-6'].status != 'NORMAL' else ('P-7' if edges['P-7'].status != 'NORMAL' else 'unknown'))
            if active_leak != 'unknown' and not Alert.objects.filter(severity='WARNING', zone='Hostels Zone', message_en__contains='imbalance').exists():
                severity = 'CRITICAL' if (edges['P-4'].status == 'BURST' or edges['P-6'].status == 'BURST' or edges['P-7'].status == 'BURST') else 'WARNING'
                alert_k = 'burst_critical' if severity == 'CRITICAL' else 'leak_warning'
                create_alert(severity, 'Hostels Zone', alert_k, pct=imbalance1, zone='Hostels Zone', pipe=active_leak)

    # Zone 2: Academic Distribution
    zone2_in = edges['P-5'].flow_rate
    zone2_out = edges['P-8'].flow_rate + edges['P-9'].flow_rate
    if zone2_in > 0:
        imbalance2 = (abs(zone2_in - zone2_out) / zone2_in) * 100.0
        if imbalance2 > 3.0:
            active_leak = 'P-5' if edges['P-5'].status != 'NORMAL' else ('P-8' if edges['P-8'].status != 'NORMAL' else ('P-9' if edges['P-9'].status != 'NORMAL' else 'unknown'))
            if active_leak != 'unknown' and not Alert.objects.filter(severity='WARNING', zone='Academic Zone', message_en__contains='imbalance').exists():
                severity = 'CRITICAL' if (edges['P-5'].status == 'BURST' or edges['P-8'].status == 'BURST' or edges['P-9'].status == 'BURST') else 'WARNING'
                alert_k = 'burst_critical' if severity == 'CRITICAL' else 'leak_warning'
                create_alert(severity, 'Academic Zone', alert_k, pct=imbalance2, zone='Academic Zone', pipe=active_leak)

    # Layer 3: Pressure Transient Analysis
    for n in nodes.values():
        p_old = old_pressures[n.name]
        p_new = n.pressure
        p_drop = p_old - p_new
        if p_drop > 0.5:
            incoming = n.incoming_edges.first()
            pipe_name = incoming.name if incoming else "unknown"
            if pipe_name != "unknown" and incoming.status == 'BURST':
                if not Alert.objects.filter(severity='CRITICAL', zone=n.name, message_en__contains='burst').exists():
                    create_alert('CRITICAL', n.name, 'burst_critical', zone=n.name, pipe=pipe_name)

    # 12. Write Telemetry Logs
    TelemetryLog.objects.filter(tick=state.current_tick).delete()
    for n in nodes.values():
        TelemetryLog.objects.create(tick=state.current_tick, node=n, parameter='pressure', value=n.pressure)
        if n.node_type == 'TANK':
            TelemetryLog.objects.create(tick=state.current_tick, node=n, parameter='level', value=n.current_level)
        TelemetryLog.objects.create(tick=state.current_tick, node=n, parameter='chlorine', value=n.chlorine)

    for e in edges.values():
        TelemetryLog.objects.create(tick=state.current_tick, edge=e, parameter='flow_rate', value=e.flow_rate)

    # Keep database small
    max_records = 300
    if TelemetryLog.objects.count() > max_records:
        ids_to_keep = TelemetryLog.objects.order_by('-timestamp')[:max_records].values_list('id', flat=True)
        TelemetryLog.objects.exclude(id__in=ids_to_keep).delete()

    return state
