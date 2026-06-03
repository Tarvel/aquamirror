from django.db import models

class SimulationState(models.Model):
    CALENDAR_CHOICES = [
        ('NORMAL', 'Normal Academic Period'),
        ('EXAMS', 'Exam Period'),
        ('HOLIDAYS', 'Semester Break/Holidays'),
        ('ASUU_STRIKE', 'ASUU Strike Outage'),
    ]
    LANG_CHOICES = [
        ('en', 'English'),
        ('yo', 'Yoruba (Èdè Yorùbá)'),
        ('ha', 'Hausa (Harshen Hausa)'),
        ('ig', 'Igbo (Asụsụ Igbo)'),
    ]

    current_tick = models.IntegerField(default=0)  # Simulation hour (0-23)
    nepa_status = models.BooleanField(default=True)  # True = Grid Power ON, False = Power Outage
    calendar_mode = models.CharField(max_length=20, choices=CALENDAR_CHOICES, default='NORMAL')
    language = models.CharField(max_length=5, choices=LANG_CHOICES, default='en')
    is_running = models.BooleanField(default=False)

    def __str__(self):
        return f"Tick: {self.current_tick} | Power: {'ON' if self.nepa_status else 'OFF'} | Mode: {self.calendar_mode}"

class Node(models.Model):
    NODE_TYPES = [
        ('PUMP', 'Pumping Station'),
        ('TANK', 'Storage Tank'),
        ('CONSUMER', 'Consumer Node'),
        ('JUNCTION', 'Junction/Treatment'),
    ]

    name = models.CharField(max_length=100, unique=True)
    node_type = models.CharField(max_length=20, choices=NODE_TYPES)
    elevation = models.FloatField(default=0.0)  # meters
    capacity = models.FloatField(default=0.0)   # Litres (for TANKs)
    current_level = models.FloatField(default=0.0) # Litres (for TANKs)
    base_demand = models.FloatField(default=0.0)  # L/min (for CONSUMERs)
    current_demand = models.FloatField(default=0.0) # L/min (for CONSUMERs)
    pressure = models.FloatField(default=0.0)     # bar
    chlorine = models.FloatField(default=0.0)     # mg/L
    status = models.CharField(max_length=50, default='ACTIVE') # ACTIVE, INACTIVE, OVERFLOW, EMPTY

    def __str__(self):
        return f"{self.name} ({self.get_node_type_display()})"

class Edge(models.Model):
    STATUS_CHOICES = [
        ('NORMAL', 'Normal'),
        ('LEAKING', 'Leaking'),
        ('BURST', 'Burst / Pipe Fracture'),
    ]
    MATERIAL_CHOICES = [
        ('uPVC', 'Unplasticized PVC'),
        ('GI', 'Galvanized Iron'),
        ('HDPE', 'High-Density Polyethylene'),
    ]

    name = models.CharField(max_length=50, unique=True)
    source = models.ForeignKey(Node, on_delete=models.CASCADE, related_name='outgoing_edges')
    target = models.ForeignKey(Node, on_delete=models.CASCADE, related_name='incoming_edges')
    material = models.CharField(max_length=20, choices=MATERIAL_CHOICES, default='uPVC')
    diameter = models.FloatField(default=100.0) # mm
    length = models.FloatField(default=100.0)   # meters
    roughness = models.FloatField(default=130.0) # Hazen-Williams C
    flow_rate = models.FloatField(default=0.0)   # L/min
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='NORMAL')
    leak_flow = models.FloatField(default=0.0)   # L/min
    failure_probability = models.FloatField(default=10.0) # Percentage (0-100)
    is_pump = models.BooleanField(default=False)
    pump_on = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.name}: {self.source.name} -> {self.target.name} ({self.status})"

class Alert(models.Model):
    SEVERITY_CHOICES = [
        ('INFO', 'Info'),
        ('WARNING', 'Warning'),
        ('CRITICAL', 'Critical Anomaly'),
    ]

    timestamp = models.DateTimeField(auto_now_add=True)
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES, default='INFO')
    zone = models.CharField(max_length=100, default='General')
    message_en = models.TextField()
    message_yo = models.TextField()
    message_ha = models.TextField()
    message_ig = models.TextField()
    acknowledged = models.BooleanField(default=False)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"[{self.severity}] {self.zone}: {self.message_en[:40]}..."

class TelemetryLog(models.Model):
    timestamp = models.DateTimeField(auto_now_add=True)
    tick = models.IntegerField()
    node = models.ForeignKey(Node, on_delete=models.CASCADE, null=True, blank=True)
    edge = models.ForeignKey(Edge, on_delete=models.CASCADE, null=True, blank=True)
    parameter = models.CharField(max_length=50) # flow_rate, pressure, level, chlorine
    value = models.FloatField()

    class Meta:
        ordering = ['timestamp']

    def __str__(self):
        item = self.node.name if self.node else self.edge.name
        return f"Tick {self.tick} | {item} | {self.parameter}: {self.value}"
