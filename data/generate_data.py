import json
import random
from datetime import datetime, timedelta

random.seed(42)

EQUIPMENT_TYPES = [
    {"id_prefix": "TRK", "type": "Heavy Utility Truck"},
    {"id_prefix": "TRK", "type": "Cargo Transport Truck"},
    {"id_prefix": "TRK", "type": "Fuel Tanker Truck"},
    {"id_prefix": "AV", "type": "Armoured Personnel Carrier"},
    {"id_prefix": "AV", "type": "Armoured Reconnaissance Vehicle"},
    {"id_prefix": "AV", "type": "Mine-Resistant Ambush Protected Vehicle"},
    {"id_prefix": "TRK", "type": "Recovery Vehicle"},
    {"id_prefix": "AV", "type": "Infantry Fighting Vehicle"},
]

FAULT_TEMPLATES = {
    "engine": [
        {
            "fault": "Engine overheating during sustained load",
            "symptoms": ["Coolant temperature warning light active", "Steam from engine bay", "Loss of power under load"],
            "diagnostic_steps": ["Check coolant level and condition", "Inspect thermostat operation", "Pressure test cooling system", "Inspect water pump impeller", "Check radiator for blockages"],
            "root_causes": ["Thermostat stuck in closed position", "Water pump impeller failure", "Radiator core blockage from debris", "Head gasket degradation"],
            "resolutions": ["Replaced thermostat and flushed cooling system", "Replaced water pump assembly", "Back-flushed and cleaned radiator core", "Replaced head gasket and resurfaced cylinder head"],
            "parts": [["Thermostat", "Coolant", "Gasket set"], ["Water pump assembly", "Coolant", "Drive belt"], ["Radiator core", "Coolant", "Hose clamps"], ["Head gasket set", "Coolant", "Head bolts"]],
            "severity": ["high", "critical"],
            "repair_hours": (4, 16),
        },
        {
            "fault": "Excessive black smoke from exhaust",
            "symptoms": ["Visible black smoke at idle and under load", "Reduced fuel economy", "Rough engine idle"],
            "diagnostic_steps": ["Inspect air filter condition", "Check fuel injector spray pattern", "Measure turbocharger boost pressure", "Analyse exhaust gas composition"],
            "root_causes": ["Clogged air filter restricting airflow", "Worn fuel injector nozzles causing over-fuelling", "Turbocharger wastegate malfunction"],
            "resolutions": ["Replaced air filter element and cleaned intake ducting", "Replaced fuel injector set and recalibrated", "Replaced turbocharger wastegate actuator"],
            "parts": [["Air filter element", "Intake gaskets"], ["Fuel injector set", "O-rings", "Fuel filter"], ["Wastegate actuator", "Turbo gasket set"]],
            "severity": ["medium", "high"],
            "repair_hours": (2, 8),
        },
        {
            "fault": "Engine fails to start",
            "symptoms": ["Cranking but no ignition", "No fuel pressure at rail", "Starter motor engages but engine does not fire"],
            "diagnostic_steps": ["Check battery voltage and starter circuit", "Verify fuel supply and pressure", "Inspect glow plugs or ignition system", "Check ECM for fault codes", "Inspect fuel shut-off solenoid"],
            "root_causes": ["Fuel shut-off solenoid failure", "Fuel lift pump failure", "Glow plug circuit failure in cold conditions", "Crankshaft position sensor fault"],
            "resolutions": ["Replaced fuel shut-off solenoid", "Replaced fuel lift pump and primed system", "Replaced glow plug set and relay", "Replaced crankshaft position sensor"],
            "parts": [["Fuel shut-off solenoid", "Wiring harness"], ["Fuel lift pump", "Fuel lines", "Fuel filter"], ["Glow plug set", "Glow plug relay"], ["Crankshaft position sensor", "Connector"]],
            "severity": ["high", "critical"],
            "repair_hours": (2, 10),
        },
        {
            "fault": "Abnormal engine knocking noise",
            "symptoms": ["Metallic knocking from engine block", "Knock intensity increases with RPM", "Oil pressure fluctuation"],
            "diagnostic_steps": ["Perform oil pressure test", "Use stethoscope to isolate knock location", "Remove oil pan and inspect bearings", "Check for piston slap"],
            "root_causes": ["Worn main bearings due to oil starvation", "Connecting rod bearing failure", "Piston pin wear"],
            "resolutions": ["Replaced main bearing set and oil pump", "Replaced connecting rod bearings and polished crankshaft journals", "Replaced piston and pin assembly"],
            "parts": [["Main bearing set", "Oil pump", "Oil filter", "Engine oil"], ["Connecting rod bearings", "Engine oil", "Oil filter"], ["Piston assembly", "Piston rings", "Gudgeon pin", "Engine oil"]],
            "severity": ["critical"],
            "repair_hours": (12, 24),
        },
        {
            "fault": "Engine oil pressure low warning",
            "symptoms": ["Oil pressure warning light illuminated", "Oil pressure gauge reading below normal", "Slight ticking noise from valve train"],
            "diagnostic_steps": ["Verify oil level and condition", "Install manual oil pressure gauge", "Inspect oil pressure sender unit", "Check oil pump relief valve"],
            "root_causes": ["Oil pressure sender unit faulty giving false reading", "Oil pump wear reducing output pressure", "Blocked oil pickup screen"],
            "resolutions": ["Replaced oil pressure sender unit", "Replaced oil pump assembly", "Cleaned oil pickup screen and replaced oil"],
            "parts": [["Oil pressure sender", "Thread sealant"], ["Oil pump", "Oil pump gasket", "Engine oil", "Oil filter"], ["Oil pickup screen", "Gasket", "Engine oil", "Oil filter"]],
            "severity": ["medium", "high"],
            "repair_hours": (1, 8),
        },
    ],
    "hydraulic": [
        {
            "fault": "Hydraulic system pressure loss",
            "symptoms": ["Slow response on hydraulic actuators", "Hydraulic fluid visible on ground", "Warning indicator for low hydraulic fluid"],
            "diagnostic_steps": ["Check hydraulic fluid reservoir level", "Inspect all hose connections and fittings", "Pressure test hydraulic circuits", "Inspect hydraulic pump output", "Check relief valve settings"],
            "root_causes": ["Hydraulic hose burst at crimped fitting", "Hydraulic pump internal seal failure", "Relief valve stuck open", "Cylinder seal blow-by"],
            "resolutions": ["Replaced failed hydraulic hose and refilled system", "Rebuilt hydraulic pump with new seal kit", "Replaced relief valve assembly", "Replaced cylinder seal kit and reassembled"],
            "parts": [["Hydraulic hose", "Hydraulic fluid", "Fittings"], ["Pump seal kit", "Hydraulic fluid", "Filter"], ["Relief valve assembly", "O-rings"], ["Cylinder seal kit", "Hydraulic fluid"]],
            "severity": ["high", "critical"],
            "repair_hours": (3, 12),
        },
        {
            "fault": "Hydraulic fluid overheating",
            "symptoms": ["Hydraulic fluid temperature gauge in red zone", "Reduced system responsiveness", "Burning smell from hydraulic reservoir area"],
            "diagnostic_steps": ["Check hydraulic oil cooler for blockage", "Verify fan operation on oil cooler", "Test hydraulic fluid viscosity", "Inspect for internal bypass leaks"],
            "root_causes": ["Hydraulic oil cooler blocked with debris", "Hydraulic fluid degradation from contamination", "Internal valve leakage causing fluid recirculation"],
            "resolutions": ["Cleaned and flushed hydraulic oil cooler", "Complete hydraulic fluid flush and replacement", "Replaced control valve block and flushed system"],
            "parts": [["Oil cooler gasket", "Hydraulic fluid"], ["Hydraulic fluid", "Hydraulic filters", "Reservoir breather"], ["Control valve block", "Hydraulic fluid", "Filters"]],
            "severity": ["medium", "high"],
            "repair_hours": (3, 8),
        },
        {
            "fault": "Hydraulic cylinder drift under load",
            "symptoms": ["Implement or turret slowly drops when stationary", "Cylinder extends or retracts without input", "Operator reports loss of position holding"],
            "diagnostic_steps": ["Inspect cylinder for external leaks", "Perform cylinder drift-down test", "Check holding valve operation", "Inspect control valve spool for wear"],
            "root_causes": ["Worn cylinder piston seals allowing internal bypass", "Counterbalance valve failure", "Control valve spool scored from contamination"],
            "resolutions": ["Replaced cylinder piston seal kit", "Replaced counterbalance valve", "Replaced control valve spool and flushed system"],
            "parts": [["Piston seal kit", "Wiper seal", "Hydraulic fluid"], ["Counterbalance valve", "O-rings"], ["Valve spool", "Hydraulic fluid", "Filters"]],
            "severity": ["medium", "high"],
            "repair_hours": (4, 10),
        },
    ],
    "transmission": [
        {
            "fault": "Transmission slipping between gears",
            "symptoms": ["RPM flare during gear changes", "Delayed engagement when shifting", "Transmission fault code stored in ECM"],
            "diagnostic_steps": ["Check transmission fluid level and condition", "Read transmission ECM fault codes", "Perform stall speed test", "Monitor shift solenoid operation", "Inspect torque converter lock-up"],
            "root_causes": ["Worn clutch pack friction material", "Shift solenoid valve failure", "Low transmission fluid from leak at output seal"],
            "resolutions": ["Overhauled transmission with new clutch packs", "Replaced shift solenoid pack", "Replaced output shaft seal and topped up fluid"],
            "parts": [["Clutch pack set", "Transmission filter", "Transmission fluid", "Gasket kit"], ["Shift solenoid pack", "Transmission fluid", "Filter"], ["Output shaft seal", "Transmission fluid"]],
            "severity": ["high", "critical"],
            "repair_hours": (6, 20),
        },
        {
            "fault": "Transmission overheating",
            "symptoms": ["Transmission temperature warning active", "Harsh or delayed shifts", "Burning smell from transmission area"],
            "diagnostic_steps": ["Check transmission cooler lines for restriction", "Inspect transmission cooler for damage", "Check fluid level and condition", "Monitor line pressure"],
            "root_causes": ["Transmission cooler lines kinked or restricted", "Transmission cooler core failure", "Worn clutch plates generating excess heat"],
            "resolutions": ["Replaced transmission cooler lines", "Replaced transmission cooler and flushed lines", "Overhauled transmission with new clutch plates and cooler flush"],
            "parts": [["Cooler lines", "Transmission fluid", "Clamps"], ["Transmission cooler", "Transmission fluid", "Hose fittings"], ["Clutch plate set", "Transmission cooler", "Fluid", "Filter", "Gasket kit"]],
            "severity": ["high", "critical"],
            "repair_hours": (4, 18),
        },
        {
            "fault": "No drive in forward or reverse",
            "symptoms": ["Engine runs normally but vehicle does not move", "No engagement felt when selecting gear", "Transmission fluid discoloured or has metallic particles"],
            "diagnostic_steps": ["Check transmission fluid level and condition for metal debris", "Perform line pressure test", "Inspect torque converter", "Check park/neutral safety switch", "Inspect drive shafts and transfer case"],
            "root_causes": ["Torque converter hub failure", "Transmission main shaft failure", "Transfer case chain stretch or failure"],
            "resolutions": ["Replaced torque converter assembly", "Replaced transmission assembly with rebuilt unit", "Replaced transfer case chain and sprockets"],
            "parts": [["Torque converter", "Transmission fluid", "Filter"], ["Remanufactured transmission", "Transmission fluid", "Filter", "Gasket kit"], ["Transfer case chain", "Sprocket set", "Transfer case fluid", "Gaskets"]],
            "severity": ["critical"],
            "repair_hours": (10, 24),
        },
    ],
    "ecm_sensor": [
        {
            "fault": "ECM communication failure",
            "symptoms": ["Multiple warning lights on dashboard", "Engine derate mode active", "Diagnostic tool unable to communicate with ECM"],
            "diagnostic_steps": ["Check ECM power supply and ground circuits", "Inspect CAN bus wiring and connectors", "Test ECM communication on diagnostic port", "Check for water ingress in ECM enclosure"],
            "root_causes": ["Corroded ECM connector pins from moisture ingress", "CAN bus wiring harness chafed causing short circuit", "ECM internal board failure"],
            "resolutions": ["Cleaned and sealed ECM connector, applied dielectric grease", "Repaired CAN bus wiring harness and re-routed away from chafe points", "Replaced ECM unit and reprogrammed"],
            "parts": [["Connector pins", "Dielectric grease", "Heat shrink"], ["Wiring harness section", "CAN bus terminating resistors", "Loom tape"], ["ECM unit", "Connector", "Software licence"]],
            "severity": ["high", "critical"],
            "repair_hours": (2, 10),
        },
        {
            "fault": "Exhaust temperature sensor fault",
            "symptoms": ["Engine derate warning active", "Fault code for exhaust temperature out of range", "Reduced engine power"],
            "diagnostic_steps": ["Read fault codes from ECM", "Measure sensor resistance at connector", "Inspect wiring from sensor to ECM", "Compare sensor reading with infrared thermometer"],
            "root_causes": ["Exhaust temperature sensor element failure", "Wiring harness damage from heat exposure", "Connector corrosion at sensor plug"],
            "resolutions": ["Replaced exhaust temperature sensor", "Replaced wiring harness section with heat-resistant loom", "Replaced connector and applied thermal protection"],
            "parts": [["Exhaust temperature sensor", "Anti-seize compound"], ["Wiring harness", "Heat-resistant sleeving", "Connectors"], ["Connector assembly", "Thermal wrap", "Cable ties"]],
            "severity": ["medium", "high"],
            "repair_hours": (1, 4),
        },
        {
            "fault": "Boost pressure sensor reading erratic",
            "symptoms": ["Intermittent power loss", "ECM fault code for boost pressure signal out of range", "Engine surging under load"],
            "diagnostic_steps": ["Read ECM fault codes and freeze frame data", "Inspect boost pressure sensor and wiring", "Check for boost leaks in intake system", "Substitute known good sensor for comparison"],
            "root_causes": ["Boost pressure sensor diaphragm failure", "Loose or cracked boost hose causing actual pressure drop", "5V reference circuit fault in ECM wiring"],
            "resolutions": ["Replaced boost pressure sensor", "Replaced boost hose and tightened all clamps", "Repaired 5V reference circuit wiring"],
            "parts": [["Boost pressure sensor", "O-ring"], ["Boost hose", "T-bolt clamps", "Silicone coupler"], ["Wiring repair kit", "Solder", "Heat shrink"]],
            "severity": ["medium", "high"],
            "repair_hours": (1, 5),
        },
        {
            "fault": "Vehicle speed sensor failure",
            "symptoms": ["Speedometer not reading", "Transmission shift pattern erratic", "ABS warning light illuminated"],
            "diagnostic_steps": ["Read fault codes from ECM and ABS module", "Inspect speed sensor and tone ring", "Measure sensor output signal with oscilloscope", "Check wiring continuity to ECM"],
            "root_causes": ["Speed sensor air gap out of specification", "Tone ring damaged or missing teeth", "Speed sensor internal failure"],
            "resolutions": ["Adjusted speed sensor air gap to specification", "Replaced tone ring and speed sensor", "Replaced speed sensor and cleared fault codes"],
            "parts": [["Feeler gauges", "Lock nut"], ["Tone ring", "Speed sensor", "Retaining hardware"], ["Speed sensor", "O-ring", "Connector"]],
            "severity": ["medium", "high"],
            "repair_hours": (1, 4),
        },
    ],
    "electrical": [
        {
            "fault": "Battery drain overnight",
            "symptoms": ["Vehicle fails to start after sitting overnight", "Battery voltage below 11V after rest period", "Multiple electrical systems resetting"],
            "diagnostic_steps": ["Perform parasitic draw test", "Isolate circuits using fuse pull method", "Inspect battery condition and load test", "Check alternator diode condition"],
            "root_causes": ["Interior light relay stuck closed drawing current", "Alternator diode leakage causing reverse current flow", "Aftermarket radio installation with constant live draw"],
            "resolutions": ["Replaced interior light relay and verified draw within spec", "Replaced alternator assembly", "Rewired aftermarket radio to switched ignition circuit"],
            "parts": [["Relay", "Fuse"], ["Alternator assembly", "Drive belt"], ["Wiring kit", "Fuse holder", "Crimp connectors"]],
            "severity": ["medium", "high"],
            "repair_hours": (2, 6),
        },
        {
            "fault": "Intermittent total electrical failure",
            "symptoms": ["All electrical systems cut out momentarily", "Dashboard lights flicker", "Engine stalls and restarts"],
            "diagnostic_steps": ["Inspect main battery cables and terminals", "Check chassis ground straps", "Inspect master battery disconnect switch", "Test battery terminal voltage under load"],
            "root_causes": ["Corroded battery terminal causing intermittent connection", "Chassis ground strap broken allowing floating ground", "Master battery switch internal contact wear"],
            "resolutions": ["Cleaned and replaced battery terminals and cables", "Replaced chassis ground strap and cleaned mounting surfaces", "Replaced master battery disconnect switch"],
            "parts": [["Battery terminals", "Battery cables", "Terminal protector spray"], ["Ground strap", "Hardware", "Contact cleaner"], ["Master disconnect switch", "Mounting hardware"]],
            "severity": ["high", "critical"],
            "repair_hours": (1, 5),
        },
        {
            "fault": "Lighting circuit failure",
            "symptoms": ["Headlights or tail lights not functioning", "Fuse blowing repeatedly", "Melted wiring insulation visible"],
            "diagnostic_steps": ["Check fuse condition and rating", "Inspect wiring harness for chafing or damage", "Test light switch and relay operation", "Measure circuit resistance"],
            "root_causes": ["Wiring harness chafed through on chassis member causing short", "Light switch failure causing overcurrent", "Corroded bulkhead connector increasing resistance"],
            "resolutions": ["Repaired wiring harness and installed protective conduit", "Replaced light switch assembly", "Replaced bulkhead connector and cleaned terminals"],
            "parts": [["Wiring", "Conduit", "Fuses", "Cable ties"], ["Light switch assembly", "Connector"], ["Bulkhead connector", "Terminal pins", "Dielectric grease"]],
            "severity": ["medium", "high"],
            "repair_hours": (2, 6),
        },
        {
            "fault": "Starter motor failure",
            "symptoms": ["Clicking sound when turning ignition key", "Starter motor engages but spins slowly", "No response from starter circuit"],
            "diagnostic_steps": ["Test battery voltage under cranking load", "Check starter motor solenoid operation", "Inspect starter motor cables and connections", "Bench test starter motor"],
            "root_causes": ["Starter motor solenoid contacts worn", "Starter motor brushes worn below service limit", "Starter motor cable connection loose or corroded"],
            "resolutions": ["Replaced starter motor solenoid", "Replaced starter motor assembly", "Cleaned and tightened starter motor cable connections"],
            "parts": [["Starter solenoid", "Contact kit"], ["Starter motor assembly", "Mounting bolts"], ["Cable lugs", "Hardware", "Contact cleaner"]],
            "severity": ["medium", "high"],
            "repair_hours": (1, 4),
        },
    ],
}

ENGINEER_NOTES_TEMPLATES = [
    "Recommend scheduling follow-up inspection in {days} days to verify repair integrity.",
    "Similar fault observed on {equip} last month. Possible fleet-wide issue with this component.",
    "Repair conducted under field conditions. Recommend depot-level verification at next scheduled service.",
    "Component showed signs of premature wear. Suggest reviewing maintenance interval for this system.",
    "Operator reported issue has been recurring for approximately {weeks} weeks before being logged.",
    "Parts sourced from emergency stock. Replenishment order required.",
    "Vehicle returned to operational status. Full function test completed satisfactorily.",
    "Root cause linked to environmental exposure. Recommend improved protective measures for {system} components.",
    "This fault pattern is consistent with contaminated fluid. Recommend full system flush at next service window.",
    "Technician noted additional wear on adjacent components. Flagged for monitoring.",
    "Operational tempo has been high on this vehicle. Suggest reduced tasking until next major service.",
    "Repair time extended due to limited access in engine bay. Suggest improved tooling for future jobs.",
]


def generate_engineer_note(equipment_type, fault_category):
    template = random.choice(ENGINEER_NOTES_TEMPLATES)
    return template.format(
        days=random.choice([30, 60, 90]),
        equip=random.choice([e["type"] for e in EQUIPMENT_TYPES]),
        weeks=random.choice([1, 2, 3, 4]),
        system=fault_category,
    )


def generate_logs(num_logs=75):
    logs = []
    start_date = datetime(2024, 1, 1)
    fault_categories = list(FAULT_TEMPLATES.keys())

    # Distribute faults roughly evenly across categories
    category_counts = {cat: 0 for cat in fault_categories}
    target_per_category = num_logs // len(fault_categories)

    for i in range(num_logs):
        # Pick category, favouring underrepresented ones
        min_count = min(category_counts.values())
        candidates = [c for c, v in category_counts.items() if v <= min_count + 2]
        category = random.choice(candidates)
        category_counts[category] += 1

        templates = FAULT_TEMPLATES[category]
        template = random.choice(templates)

        equipment = random.choice(EQUIPMENT_TYPES)
        equip_num = random.randint(100, 999)
        equipment_id = f"{equipment['id_prefix']}-{equip_num}"

        date = start_date + timedelta(days=random.randint(0, 365))

        variant_idx = random.randint(0, len(template["root_causes"]) - 1)

        min_hours, max_hours = template["repair_hours"]
        repair_hours = round(random.uniform(min_hours, max_hours), 1)

        log = {
            "log_id": f"ML-2024-{str(i + 1).zfill(4)}",
            "date": date.strftime("%Y-%m-%d"),
            "equipment_id": equipment_id,
            "equipment_type": equipment["type"],
            "fault_description": template["fault"],
            "symptoms": template["symptoms"],
            "diagnostic_steps": template["diagnostic_steps"],
            "root_cause": template["root_causes"][variant_idx],
            "resolution": template["resolutions"][variant_idx],
            "parts_replaced": template["parts"][variant_idx],
            "repair_time_hours": repair_hours,
            "engineer_notes": generate_engineer_note(equipment["type"], category),
            "severity": random.choice(template["severity"]),
        }

        logs.append(log)

    # Sort by date
    logs.sort(key=lambda x: x["date"])

    return logs


if __name__ == "__main__":
    logs = generate_logs(75)
    output_path = "maintenance_logs.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(logs, f, indent=2, ensure_ascii=False)
    print(f"Generated {len(logs)} maintenance logs saved to {output_path}")
