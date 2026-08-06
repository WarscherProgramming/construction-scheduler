"""Versioned built-in construction scope taxonomy.

This module is pure: no ORM, no session, no configuration, no I/O. Assertions
pin ``concept_code`` and ``taxonomy_version`` so a later taxonomy release
cannot rewrite historical meaning. Providers may only select codes that
already exist here; they never introduce concepts or aliases.
"""

from dataclasses import dataclass
import unicodedata


TAXONOMY_VERSION = "construction-scope-1"
TAXONOMY_RELEASED_ON = "2026-08-05"
SUPPORTED_TAXONOMY_VERSIONS = (TAXONOMY_VERSION,)

SCOPE_CATEGORIES = (
    "general_requirements",
    "demolition",
    "sitework",
    "concrete",
    "masonry",
    "metals",
    "wood_plastics_composites",
    "thermal_moisture_protection",
    "openings",
    "finishes",
    "specialties",
    "equipment",
    "furnishings",
    "special_construction",
    "conveying_equipment",
    "fire_suppression",
    "plumbing",
    "hvac",
    "electrical",
    "communications",
    "electronic_safety_security",
    "utilities",
    "process_equipment",
    "controls",
    "commissioning",
    "temporary_work",
    "closeout",
    "coordination",
    "procurement",
    "submittal",
    "testing_inspection",
    "owner_furnished",
    "contractor_furnished",
    "delegated_design",
    "allowance",
    "alternate",
    "exclusion",
    "other",
)

SCOPE_KINDS = (
    "physical_element",
    "system",
    "activity",
    "responsibility",
    "deliverable",
    "testing_requirement",
    "coordination_requirement",
    "procurement_item",
    "exclusion",
    "allowance",
    "alternate",
    "other",
)

CATEGORY_LABELS = {
    "general_requirements": "General Requirements",
    "demolition": "Demolition",
    "sitework": "Sitework",
    "concrete": "Concrete",
    "masonry": "Masonry",
    "metals": "Metals",
    "wood_plastics_composites": "Wood, Plastics, and Composites",
    "thermal_moisture_protection": "Thermal and Moisture Protection",
    "openings": "Openings",
    "finishes": "Finishes",
    "specialties": "Specialties",
    "equipment": "Equipment",
    "furnishings": "Furnishings",
    "special_construction": "Special Construction",
    "conveying_equipment": "Conveying Equipment",
    "fire_suppression": "Fire Suppression",
    "plumbing": "Plumbing",
    "hvac": "HVAC",
    "electrical": "Electrical",
    "communications": "Communications",
    "electronic_safety_security": "Electronic Safety and Security",
    "utilities": "Utilities",
    "process_equipment": "Process Equipment",
    "controls": "Controls",
    "commissioning": "Commissioning",
    "temporary_work": "Temporary Work",
    "closeout": "Closeout",
    "coordination": "Coordination",
    "procurement": "Procurement",
    "submittal": "Submittal",
    "testing_inspection": "Testing and Inspection",
    "owner_furnished": "Owner Furnished",
    "contractor_furnished": "Contractor Furnished",
    "delegated_design": "Delegated Design",
    "allowance": "Allowance",
    "alternate": "Alternate",
    "exclusion": "Exclusion",
    "other": "Other",
}

SCOPE_KIND_LABELS = {
    "physical_element": "Physical Element",
    "system": "System",
    "activity": "Activity",
    "responsibility": "Responsibility",
    "deliverable": "Deliverable",
    "testing_requirement": "Testing Requirement",
    "coordination_requirement": "Coordination Requirement",
    "procurement_item": "Procurement Item",
    "exclusion": "Exclusion",
    "allowance": "Allowance",
    "alternate": "Alternate",
    "other": "Other",
}


@dataclass(frozen=True)
class ScopeConcept:
    code: str
    name: str
    category: str
    scope_kind: str
    description: str
    aliases: tuple[str, ...] = ()
    parent_code: str | None = None
    default_unit: str | None = None
    status: str = "active"
    created_at: str = TAXONOMY_RELEASED_ON
    deprecated_at: str | None = None


# Controlled canonical units. Quantities are never inferred; a unit is
# normalized only when the provider or author supplies one.
CANONICAL_UNITS = (
    "each",
    "square_foot",
    "linear_foot",
    "cubic_yard",
    "square_yard",
    "lump_sum",
    "gallon",
    "pound",
    "ton",
    "cfm",
    "gpm",
    "kilowatt",
    "kilovolt_ampere",
    "ton_refrigeration",
    "hour",
    "day",
    "set",
    "pair",
    "sheet",
)

_UNIT_ALIAS_SOURCE = {
    "each": ("ea", "each", "eaches", "pc", "piece", "pieces", "no", "nos"),
    "square_foot": ("sf", "sq ft", "sqft", "square foot", "square feet", "ft2"),
    "linear_foot": ("lf", "lin ft", "linft", "linear foot", "linear feet"),
    "cubic_yard": ("cy", "cu yd", "cubic yard", "cubic yards"),
    "square_yard": ("sy", "sq yd", "square yard", "square yards"),
    "lump_sum": ("ls", "lump sum", "lumpsum", "l s"),
    "gallon": ("gal", "gallon", "gallons"),
    "pound": ("lb", "lbs", "pound", "pounds"),
    "ton": ("ton", "tons", "tn"),
    "cfm": ("cfm", "cubic feet per minute"),
    "gpm": ("gpm", "gallons per minute"),
    "kilowatt": ("kw", "kilowatt", "kilowatts"),
    "kilovolt_ampere": ("kva", "kilovolt ampere", "kilovolt amperes"),
    "ton_refrigeration": ("tr", "ton refrigeration", "tons refrigeration", "rt"),
    "hour": ("hr", "hrs", "hour", "hours"),
    "day": ("day", "days"),
    "set": ("set", "sets"),
    "pair": ("pair", "pairs", "pr"),
    "sheet": ("sheet", "sheets", "sht"),
}


CONCEPTS = (
    # --- general requirements / coordination / closeout -------------------
    ScopeConcept(
        "general_requirements.mobilization", "Mobilization", "general_requirements",
        "activity", "Mobilization and demobilization of crews, equipment, and facilities.",
        ("mobilization", "demobilization", "mob", "mob and demob"),
        default_unit="lump_sum",
    ),
    ScopeConcept(
        "general_requirements.project_management", "Project Management",
        "general_requirements", "responsibility",
        "Project management, supervision, and administrative staffing scope.",
        ("project management", "supervision", "project supervision", "site management"),
    ),
    ScopeConcept(
        "general_requirements.permits_fees", "Permits and Fees", "general_requirements",
        "responsibility", "Permits, fees, and authority-having-jurisdiction applications.",
        ("permit", "permits", "permit fees", "fees", "ahj fees"),
    ),
    ScopeConcept(
        "general_requirements.safety_program", "Safety Program", "general_requirements",
        "responsibility", "Site safety program, protection, and required safety personnel.",
        ("safety", "safety program", "site safety", "ppe", "safety personnel"),
    ),
    ScopeConcept(
        "coordination.trade_coordination", "Trade Coordination", "coordination",
        "coordination_requirement",
        "Coordination between trades, including interface and sequencing obligations.",
        ("trade coordination", "coordination", "interface coordination"),
    ),
    ScopeConcept(
        "coordination.bim_coordination", "BIM Coordination", "coordination",
        "coordination_requirement",
        "Model-based coordination, clash detection, and shop-model deliverables.",
        ("bim", "bim coordination", "clash detection", "model coordination"),
    ),
    ScopeConcept(
        "coordination.mep_coordination", "MEP Coordination", "coordination",
        "coordination_requirement",
        "Mechanical, electrical, and plumbing coordination and routing resolution.",
        ("mep coordination", "mep", "mechanical electrical plumbing coordination"),
    ),
    ScopeConcept(
        "closeout.record_documents", "Record Documents", "closeout", "deliverable",
        "As-built and record documentation required at project closeout.",
        ("as-built", "as builts", "as-builts", "record drawings", "record documents"),
    ),
    ScopeConcept(
        "closeout.om_manuals", "Operation and Maintenance Manuals", "closeout",
        "deliverable", "Operation and maintenance manuals and owner training material.",
        ("o&m", "o and m manuals", "om manuals", "operation and maintenance manuals"),
    ),
    ScopeConcept(
        "closeout.warranty", "Warranty", "closeout", "deliverable",
        "Warranty obligations, durations, and warranty documentation.",
        ("warranty", "warranties", "guarantee", "guaranty"),
    ),
    ScopeConcept(
        "closeout.owner_training", "Owner Training", "closeout", "deliverable",
        "Owner instruction and training sessions for installed systems.",
        ("owner training", "training", "operator training"),
    ),

    # --- demolition / sitework / utilities --------------------------------
    ScopeConcept(
        "demolition.selective_demolition", "Selective Demolition", "demolition",
        "activity", "Selective removal of existing construction within the work area.",
        ("selective demolition", "demo", "demolition", "removals"),
    ),
    ScopeConcept(
        "demolition.hazardous_material_abatement", "Hazardous Material Abatement",
        "demolition", "activity",
        "Abatement of asbestos, lead, or other regulated hazardous materials.",
        ("abatement", "asbestos abatement", "lead abatement", "hazmat"),
    ),
    ScopeConcept(
        "sitework.earthwork", "Earthwork", "sitework", "activity",
        "Excavation, backfill, grading, and compaction.",
        ("earthwork", "excavation", "grading", "backfill", "cut and fill"),
        default_unit="cubic_yard",
    ),
    ScopeConcept(
        "sitework.paving", "Paving", "sitework", "physical_element",
        "Asphalt or concrete paving, curbs, and pavement markings.",
        ("paving", "asphalt", "pavement", "curb and gutter", "striping"),
        default_unit="square_foot",
    ),
    ScopeConcept(
        "sitework.landscaping", "Landscaping", "sitework", "physical_element",
        "Planting, irrigation, and landscape restoration.",
        ("landscaping", "landscape", "planting", "irrigation", "sod"),
    ),
    ScopeConcept(
        "utilities.site_utilities", "Site Utilities", "utilities", "system",
        "Underground site utility distribution outside the building line.",
        ("site utilities", "underground utilities", "site utility"),
    ),
    ScopeConcept(
        "utilities.storm_drainage", "Storm Drainage", "utilities", "system",
        "Storm drainage collection, piping, and detention.",
        ("storm drainage", "storm sewer", "storm water", "stormwater"),
    ),
    ScopeConcept(
        "utilities.sanitary_sewer", "Sanitary Sewer", "utilities", "system",
        "Sanitary sewer collection and discharge outside the building line.",
        ("sanitary sewer", "sanitary", "sewer"),
    ),

    # --- structure --------------------------------------------------------
    ScopeConcept(
        "concrete.cast_in_place_concrete", "Cast-in-Place Concrete", "concrete",
        "physical_element", "Cast-in-place concrete including formwork and placement.",
        ("cast in place concrete", "cip concrete", "concrete", "formwork"),
        default_unit="cubic_yard",
    ),
    ScopeConcept(
        "concrete.concrete_reinforcement", "Concrete Reinforcement", "concrete",
        "physical_element", "Reinforcing steel, welded wire, and accessories.",
        ("rebar", "reinforcing steel", "reinforcement", "welded wire"),
        default_unit="pound",
    ),
    ScopeConcept(
        "concrete.concrete_slab", "Concrete Slab", "concrete", "physical_element",
        "Slabs on grade and elevated slabs.",
        ("slab", "slab on grade", "sog", "elevated slab", "topping slab"),
        default_unit="square_foot",
    ),
    ScopeConcept(
        "masonry.unit_masonry", "Unit Masonry", "masonry", "physical_element",
        "Concrete unit masonry, brick, and stone masonry assemblies.",
        ("masonry", "cmu", "unit masonry", "brick", "block"),
        default_unit="square_foot",
    ),
    ScopeConcept(
        "metals.structural_steel", "Structural Steel", "metals", "physical_element",
        "Structural steel framing, connections, and erection.",
        ("structural steel", "steel framing", "steel erection"),
        default_unit="ton",
    ),
    ScopeConcept(
        "metals.metal_deck", "Metal Deck", "metals", "physical_element",
        "Composite and non-composite metal floor and roof deck.",
        ("metal deck", "steel deck", "roof deck", "floor deck"),
        default_unit="square_foot",
    ),
    ScopeConcept(
        "metals.miscellaneous_metals", "Miscellaneous Metals", "metals",
        "physical_element", "Railings, ladders, embeds, and miscellaneous fabrications.",
        ("misc metals", "miscellaneous metals", "railings", "handrail", "ladders"),
    ),
    ScopeConcept(
        "wood_plastics_composites.rough_carpentry", "Rough Carpentry",
        "wood_plastics_composites", "physical_element",
        "Structural and non-structural rough carpentry and blocking.",
        ("rough carpentry", "blocking", "framing", "wood framing"),
    ),
    ScopeConcept(
        "wood_plastics_composites.architectural_millwork", "Architectural Millwork",
        "wood_plastics_composites", "physical_element",
        "Finish carpentry, architectural woodwork, casework, and countertops.",
        ("millwork", "casework", "architectural woodwork", "finish carpentry",
         "cabinets", "countertops"),
        default_unit="linear_foot",
    ),

    # --- envelope ---------------------------------------------------------
    ScopeConcept(
        "thermal_moisture_protection.roofing", "Roofing",
        "thermal_moisture_protection", "system",
        "Roofing membrane, insulation, flashing, and roof accessories.",
        ("roofing", "roof", "membrane roofing", "tpo", "epdm", "roof system"),
        default_unit="square_foot",
    ),
    ScopeConcept(
        "thermal_moisture_protection.waterproofing", "Waterproofing",
        "thermal_moisture_protection", "system",
        "Below-grade and above-grade waterproofing and dampproofing.",
        ("waterproofing", "dampproofing", "water proofing"),
    ),
    ScopeConcept(
        "thermal_moisture_protection.insulation", "Insulation",
        "thermal_moisture_protection", "physical_element",
        "Thermal and acoustic building insulation.",
        ("insulation", "thermal insulation", "batt insulation", "rigid insulation"),
        default_unit="square_foot",
    ),
    ScopeConcept(
        "thermal_moisture_protection.firestopping", "Firestopping",
        "thermal_moisture_protection", "activity",
        "Through-penetration firestopping and joint fire protection.",
        ("firestopping", "fire stopping", "fire caulking", "penetration firestop"),
    ),
    ScopeConcept(
        "openings.doors_frames", "Doors and Frames", "openings", "physical_element",
        "Door leaves, frames, and related opening assemblies.",
        ("doors", "door", "hollow metal", "frames", "door frames"),
        default_unit="each",
    ),
    ScopeConcept(
        "openings.door_hardware", "Door Hardware", "openings", "physical_element",
        "Finish hardware sets, closers, exit devices, and access-control interfaces.",
        ("door hardware", "hardware", "finish hardware", "hardware sets"),
        default_unit="set",
    ),
    ScopeConcept(
        "openings.glazing_curtain_wall", "Glazing and Curtain Wall", "openings",
        "system", "Storefront, curtain wall, windows, and glazing assemblies.",
        ("glazing", "curtain wall", "storefront", "windows", "glass"),
        default_unit="square_foot",
    ),
    ScopeConcept(
        "openings.overhead_doors", "Overhead Doors", "openings", "physical_element",
        "Overhead coiling, sectional, and specialty large openings.",
        ("overhead door", "coiling door", "sectional door", "roll up door"),
        default_unit="each",
    ),

    # --- interiors --------------------------------------------------------
    ScopeConcept(
        "finishes.gypsum_board_assemblies", "Gypsum Board Assemblies", "finishes",
        "physical_element", "Metal stud framing, gypsum board, and interior partitions.",
        ("drywall", "gypsum board", "gyp board", "partitions", "metal studs"),
        default_unit="square_foot",
    ),
    ScopeConcept(
        "finishes.acoustical_ceilings", "Acoustical Ceilings", "finishes",
        "physical_element", "Acoustical ceiling grid, tile, and specialty ceilings.",
        ("acoustical ceiling", "act", "ceiling grid", "ceiling tile", "ceilings"),
        default_unit="square_foot",
    ),
    ScopeConcept(
        "finishes.flooring", "Flooring", "finishes", "physical_element",
        "Resilient, carpet, tile, and specialty floor finishes.",
        ("flooring", "floor finish", "carpet", "vct", "lvt", "tile flooring"),
        default_unit="square_foot",
    ),
    ScopeConcept(
        "finishes.painting_coatings", "Painting and Coatings", "finishes", "activity",
        "Field painting, coatings, and special protective finishes.",
        ("painting", "paint", "coatings", "field painting"),
        default_unit="square_foot",
    ),
    ScopeConcept(
        "specialties.signage", "Signage", "specialties", "physical_element",
        "Interior and exterior signage, including code-required signage.",
        ("signage", "signs", "room signage", "ada signage"),
        default_unit="each",
    ),
    ScopeConcept(
        "specialties.toilet_accessories", "Toilet Accessories", "specialties",
        "physical_element", "Toilet partitions, accessories, and washroom specialties.",
        ("toilet accessories", "toilet partitions", "restroom accessories",
         "bathroom accessories"),
    ),
    ScopeConcept(
        "furnishings.window_treatments", "Window Treatments", "furnishings",
        "physical_element", "Blinds, shades, and interior window treatments.",
        ("window treatments", "blinds", "shades", "roller shades"),
    ),
    ScopeConcept(
        "furnishings.furniture", "Furniture", "furnishings", "physical_element",
        "Loose and fixed furniture within the project scope.",
        ("furniture", "ff&e", "ffe", "furnishings"),
    ),

    # --- equipment --------------------------------------------------------
    ScopeConcept(
        "equipment.food_service_equipment", "Food Service Equipment", "equipment",
        "physical_element",
        "Commercial kitchen and food service equipment and related connections.",
        ("kitchen equipment", "food service equipment", "commercial kitchen",
         "kitchen appliances", "fse"),
        default_unit="each",
    ),
    ScopeConcept(
        "equipment.medical_equipment", "Medical Equipment", "equipment",
        "physical_element", "Medical and clinical equipment and support requirements.",
        ("medical equipment", "clinical equipment", "imaging equipment"),
        default_unit="each",
    ),
    ScopeConcept(
        "equipment.laboratory_equipment", "Laboratory Equipment", "equipment",
        "physical_element", "Laboratory casework-mounted and freestanding equipment.",
        ("laboratory equipment", "lab equipment", "fume hood", "fume hoods"),
        default_unit="each",
    ),
    ScopeConcept(
        "conveying_equipment.elevators", "Elevators", "conveying_equipment", "system",
        "Passenger and freight elevators, lifts, and conveying systems.",
        ("elevator", "elevators", "lift", "conveying"),
        default_unit="each",
    ),
    ScopeConcept(
        "special_construction.pre_engineered_structures",
        "Pre-Engineered Structures", "special_construction", "physical_element",
        "Pre-engineered metal buildings, canopies, and packaged structures.",
        ("pre-engineered", "pre engineered building", "pemb", "canopy"),
    ),
    ScopeConcept(
        "process_equipment.process_piping", "Process Piping", "process_equipment",
        "system", "Process and specialty piping systems outside standard plumbing.",
        ("process piping", "specialty piping", "process pipe"),
        default_unit="linear_foot",
    ),

    # --- fire / plumbing / hvac -------------------------------------------
    ScopeConcept(
        "fire_suppression.sprinkler_system", "Sprinkler System", "fire_suppression",
        "system", "Automatic fire sprinkler piping, heads, and appurtenances.",
        ("sprinkler", "sprinklers", "fire sprinkler", "fire protection",
         "sprinkler system", "sprinkler heads"),
    ),
    ScopeConcept(
        "fire_suppression.fire_pump", "Fire Pump", "fire_suppression",
        "physical_element", "Fire pump, controller, and associated piping.",
        ("fire pump", "fire pump controller"),
        default_unit="each",
    ),
    ScopeConcept(
        "plumbing.plumbing_fixture", "Plumbing Fixture", "plumbing",
        "physical_element",
        "Plumbing fixtures including carriers, trim, and fixture connections.",
        ("plumbing fixture", "plumbing fixtures", "fixtures", "water closet",
         "lavatory", "sink", "urinal"),
        default_unit="each",
    ),
    ScopeConcept(
        "plumbing.domestic_water_piping", "Domestic Water Piping", "plumbing",
        "system", "Domestic hot and cold water distribution piping and insulation.",
        ("domestic water", "water piping", "dcw", "dhw", "domestic water piping"),
        default_unit="linear_foot",
    ),
    ScopeConcept(
        "plumbing.sanitary_waste_vent", "Sanitary Waste and Vent", "plumbing",
        "system", "Sanitary waste, drain, and vent piping within the building.",
        ("waste and vent", "sanitary waste", "dwv", "drain waste vent"),
        default_unit="linear_foot",
    ),
    ScopeConcept(
        "plumbing.water_heater", "Water Heater", "plumbing", "physical_element",
        "Domestic water heaters and associated storage.",
        ("water heater", "water heaters", "domestic water heater", "dhw heater"),
        default_unit="each",
    ),
    ScopeConcept(
        "hvac.air_handling_unit", "Air Handling Unit", "hvac", "physical_element",
        "Air handling units, rooftop units, and packaged air handling equipment.",
        ("air handling unit", "ahu", "ahus", "air handler", "rooftop unit", "rtu"),
        default_unit="each",
    ),
    ScopeConcept(
        "hvac.variable_air_volume_box", "Variable Air Volume Box", "hvac",
        "physical_element", "VAV terminal units, including reheat coils.",
        ("vav", "vav box", "vav boxes", "variable air volume box", "terminal unit"),
        default_unit="each",
    ),
    ScopeConcept(
        "hvac.ductwork", "Ductwork", "hvac", "physical_element",
        "Supply, return, exhaust ductwork, and duct accessories.",
        ("ductwork", "duct", "ducts", "sheet metal", "ductwork accessories"),
        default_unit="pound",
    ),
    ScopeConcept(
        "hvac.hydronic_piping", "Hydronic Piping", "hvac", "system",
        "Chilled water, hot water, and condenser water piping.",
        ("hydronic piping", "chilled water", "hot water piping", "condenser water"),
        default_unit="linear_foot",
    ),
    ScopeConcept(
        "hvac.chiller", "Chiller", "hvac", "physical_element",
        "Chillers and associated cooling plant equipment.",
        ("chiller", "chillers", "cooling plant"),
        default_unit="ton_refrigeration",
    ),
    ScopeConcept(
        "hvac.boiler", "Boiler", "hvac", "physical_element",
        "Boilers and associated heating plant equipment.",
        ("boiler", "boilers", "heating plant"),
        default_unit="each",
    ),
    ScopeConcept(
        "hvac.exhaust_fan", "Exhaust Fan", "hvac", "physical_element",
        "Exhaust, supply, and specialty fans.",
        ("exhaust fan", "fans", "ef", "supply fan"),
        default_unit="each",
    ),
    ScopeConcept(
        "hvac.hvac_general", "General HVAC Scope", "hvac", "system",
        "Deprecated broad HVAC scope retained so historical assertions that "
        "pinned this code remain resolvable. Use a specific HVAC concept.",
        ("general hvac", "hvac general"),
        status="deprecated",
        deprecated_at=TAXONOMY_RELEASED_ON,
    ),

    # --- electrical / low voltage -----------------------------------------
    ScopeConcept(
        "electrical.lighting_fixture", "Lighting Fixture", "electrical",
        "physical_element", "Interior and exterior lighting fixtures and lamps.",
        ("light fixture", "light fixtures", "luminaire", "luminaires", "lighting",
         "lighting fixtures", "fixtures lighting"),
        default_unit="each",
    ),
    ScopeConcept(
        "electrical.lighting_control", "Lighting Control", "electrical", "system",
        "Lighting control devices, relays, sensors, and control panels.",
        ("lighting control", "lighting controls", "occupancy sensor", "dimming"),
    ),
    ScopeConcept(
        "electrical.receptacle", "Receptacle", "electrical", "physical_element",
        "Receptacles, outlets, and associated device boxes.",
        ("receptacle", "receptacles", "outlet", "outlets", "device", "duplex"),
        default_unit="each",
    ),
    ScopeConcept(
        "electrical.panelboard", "Panelboard", "electrical", "physical_element",
        "Panelboards, switchboards, and distribution equipment.",
        ("panelboard", "panel", "panels", "switchboard", "distribution panel"),
        default_unit="each",
    ),
    ScopeConcept(
        "electrical.feeder_branch_wiring", "Feeder and Branch Wiring", "electrical",
        "system", "Feeders, branch circuits, conduit, and wire.",
        ("feeder", "feeders", "branch wiring", "conduit and wire", "branch circuits"),
        default_unit="linear_foot",
    ),
    ScopeConcept(
        "electrical.generator", "Generator", "electrical", "physical_element",
        "Standby or emergency generators and transfer equipment.",
        ("generator", "generators", "genset", "emergency generator",
         "automatic transfer switch", "ats"),
        default_unit="each",
    ),
    ScopeConcept(
        "electrical.grounding", "Grounding", "electrical", "system",
        "Grounding and bonding systems.",
        ("grounding", "bonding", "ground grid", "earthing"),
    ),
    ScopeConcept(
        "communications.structured_cabling", "Structured Cabling", "communications",
        "system", "Voice and data structured cabling, racks, and pathways.",
        ("structured cabling", "data cabling", "low voltage cabling", "cat6",
         "telecom cabling"),
    ),
    ScopeConcept(
        "communications.audio_visual", "Audio Visual", "communications", "system",
        "Audio-visual systems, displays, and related infrastructure.",
        ("audio visual", "av", "a/v", "av systems"),
    ),
    ScopeConcept(
        "electronic_safety_security.fire_alarm", "Fire Alarm",
        "electronic_safety_security", "system",
        "Fire alarm control panels, devices, and notification appliances.",
        ("fire alarm", "fa", "fa device", "fire alarm device", "facp",
         "notification appliance"),
        default_unit="each",
    ),
    ScopeConcept(
        "electronic_safety_security.access_control", "Access Control",
        "electronic_safety_security", "system",
        "Access control, card readers, and door position monitoring.",
        ("access control", "card reader", "card readers", "badge reader"),
    ),
    ScopeConcept(
        "electronic_safety_security.video_surveillance", "Video Surveillance",
        "electronic_safety_security", "system",
        "Video surveillance cameras, recorders, and monitoring.",
        ("video surveillance", "cctv", "cameras", "security cameras"),
    ),
    ScopeConcept(
        "controls.building_automation", "Building Automation", "controls", "system",
        "Building automation system, controllers, and sequences of operation.",
        ("controls", "bas", "building automation", "ddc", "temperature controls",
         "sequence of operation"),
    ),

    # --- process obligations ----------------------------------------------
    ScopeConcept(
        "submittal.shop_drawings", "Shop Drawings", "submittal", "deliverable",
        "Shop drawing submittal obligations.",
        ("shop drawings", "shop drawing", "shops"),
    ),
    ScopeConcept(
        "submittal.product_data", "Product Data", "submittal", "deliverable",
        "Product data, cut sheets, and material submittal obligations.",
        ("product data", "cut sheets", "cut sheet", "material submittal"),
    ),
    ScopeConcept(
        "submittal.samples", "Samples", "submittal", "deliverable",
        "Physical samples and mockup submittal obligations.",
        ("samples", "sample", "mockup", "mock-up"),
    ),
    ScopeConcept(
        "testing_inspection.special_inspection", "Special Inspection",
        "testing_inspection", "testing_requirement",
        "Code-required special inspection and structural observation.",
        ("special inspection", "special inspections", "structural observation"),
    ),
    ScopeConcept(
        "testing_inspection.testing_balancing", "Testing and Balancing",
        "testing_inspection", "testing_requirement",
        "Testing, adjusting, and balancing of mechanical systems.",
        ("testing and balancing", "tab", "test and balance", "air balance",
         "balancing"),
    ),
    ScopeConcept(
        "testing_inspection.material_testing", "Material Testing",
        "testing_inspection", "testing_requirement",
        "Material sampling and laboratory testing requirements.",
        ("material testing", "concrete testing", "soil testing", "lab testing"),
    ),
    ScopeConcept(
        "commissioning.system_commissioning", "System Commissioning",
        "commissioning", "testing_requirement",
        "Commissioning, functional performance testing, and related support.",
        ("commissioning", "cx", "functional testing",
         "functional performance testing"),
    ),
    ScopeConcept(
        "delegated_design.delegated_engineering", "Delegated Engineering",
        "delegated_design", "responsibility",
        "Delegated design and engineering obligations requiring a sealed design.",
        ("delegated design", "deferred submittal", "engineered by contractor",
         "sealed design"),
    ),
    ScopeConcept(
        "procurement.long_lead_equipment", "Long Lead Equipment", "procurement",
        "procurement_item", "Long-lead procurement items and their delivery constraints.",
        ("long lead", "long lead equipment", "long-lead", "lead time"),
    ),
    ScopeConcept(
        "procurement.material_procurement", "Material Procurement", "procurement",
        "procurement_item", "Material purchase, delivery, and storage obligations.",
        ("material procurement", "purchase", "procurement", "material delivery"),
    ),
    ScopeConcept(
        "temporary_work.temporary_facilities", "Temporary Facilities",
        "temporary_work", "activity",
        "Temporary power, water, enclosures, protection, and site facilities.",
        ("temporary facilities", "temp power", "temporary power", "temp heat",
         "temporary protection", "winter protection"),
    ),
    ScopeConcept(
        "temporary_work.scaffolding", "Scaffolding", "temporary_work", "activity",
        "Scaffolding, hoisting, and access equipment.",
        ("scaffolding", "scaffold", "hoisting", "man lift", "access equipment"),
    ),

    # --- responsibility / commercial --------------------------------------
    ScopeConcept(
        "owner_furnished.owner_furnished_equipment", "Owner Furnished Equipment",
        "owner_furnished", "responsibility",
        "Equipment furnished by the owner, with installation responsibility stated.",
        ("owner furnished equipment", "ofe", "owner furnished", "ofci",
         "owner furnished contractor installed"),
    ),
    ScopeConcept(
        "contractor_furnished.contractor_furnished_equipment",
        "Contractor Furnished Equipment", "contractor_furnished", "responsibility",
        "Equipment furnished and installed by the contractor.",
        ("contractor furnished equipment", "cfe", "contractor furnished", "cfci",
         "furnish and install"),
    ),
    ScopeConcept(
        "allowance.cash_allowance", "Cash Allowance", "allowance", "allowance",
        "Stated cash allowance carried in the proposal or contract.",
        ("allowance", "cash allowance", "allowances"),
        default_unit="lump_sum",
    ),
    ScopeConcept(
        "alternate.bid_alternate", "Bid Alternate", "alternate", "alternate",
        "Additive or deductive bid alternate.",
        ("alternate", "alternates", "bid alternate", "add alternate",
         "deduct alternate"),
    ),
    ScopeConcept(
        "exclusion.stated_exclusion", "Stated Exclusion", "exclusion", "exclusion",
        "Explicitly stated exclusion from the scope of work.",
        ("exclusion", "exclusions", "excluded", "not included", "by others"),
    ),
    ScopeConcept(
        "exclusion.clarification", "Scope Clarification", "exclusion", "exclusion",
        "Stated qualification or clarification limiting the scope of work.",
        ("clarification", "clarifications", "qualification", "qualifications"),
    ),
    ScopeConcept(
        "other.other_scope", "Other Scope", "other", "other",
        "Scope that does not map to a more specific controlled concept.",
        ("other", "other scope", "miscellaneous"),
    ),
)


def _normalize(value: str) -> str:
    """NFKC + case-fold + whitespace collapse. Used for alias comparison."""
    normalized = unicodedata.normalize("NFKC", value or "")
    return " ".join(normalized.casefold().split())


def normalize_alias(value: str) -> str:
    return _normalize(value)


def normalize_unit(value: str | None) -> str | None:
    """Map a supplied unit onto a canonical unit, or None when unrecognized.

    Units are never invented. An unrecognized unit returns ``None`` so the
    caller can decide whether to reject or drop it; it is not guessed.
    """
    if value is None:
        return None
    normalized = _normalize(value).replace(".", "")
    if not normalized:
        return None
    if normalized in CANONICAL_UNITS:
        return normalized
    return _UNIT_ALIAS_TO_CANONICAL.get(normalized)


CONCEPT_BY_CODE = {concept.code: concept for concept in CONCEPTS}
ACTIVE_CONCEPTS = tuple(
    concept for concept in CONCEPTS if concept.status == "active"
)
CONCEPT_CODES = frozenset(CONCEPT_BY_CODE)
ACTIVE_CONCEPT_CODES = frozenset(concept.code for concept in ACTIVE_CONCEPTS)

_ALIAS_TO_CODE: dict[str, str] = {}
for _concept in CONCEPTS:
    for _alias in (_concept.name, *_concept.aliases):
        _normalized_alias = _normalize(_alias)
        if not _normalized_alias:
            raise RuntimeError(
                f"Scope taxonomy alias cannot be blank for {_concept.code}"
            )
        _existing = _ALIAS_TO_CODE.get(_normalized_alias)
        if _existing is not None and _existing != _concept.code:
            raise RuntimeError(
                "Scope taxonomy alias collision: "
                f"{_normalized_alias!r} maps to both "
                f"{_existing} and {_concept.code}"
            )
        _ALIAS_TO_CODE[_normalized_alias] = _concept.code
ALIAS_TO_CODE = dict(_ALIAS_TO_CODE)

_UNIT_ALIAS_TO_CANONICAL: dict[str, str] = {}
for _canonical, _aliases in _UNIT_ALIAS_SOURCE.items():
    if _canonical not in CANONICAL_UNITS:
        raise RuntimeError(f"Unknown canonical unit {_canonical}")
    for _unit_alias in _aliases:
        _normalized_unit = _normalize(_unit_alias).replace(".", "")
        if _normalized_unit in _UNIT_ALIAS_TO_CANONICAL:
            raise RuntimeError(f"Unit alias collision: {_normalized_unit!r}")
        _UNIT_ALIAS_TO_CANONICAL[_normalized_unit] = _canonical
UNIT_ALIAS_TO_CANONICAL = dict(_UNIT_ALIAS_TO_CANONICAL)


# Import-time integrity: codes unique, categories/kinds/status allowlisted,
# parent codes resolvable, deprecated concepts dated.
if len(CONCEPT_BY_CODE) != len(CONCEPTS):
    raise RuntimeError("Scope taxonomy contains duplicate concept codes")
for _concept in CONCEPTS:
    if _concept.category not in SCOPE_CATEGORIES:
        raise RuntimeError(f"Unknown scope category for {_concept.code}")
    if _concept.scope_kind not in SCOPE_KINDS:
        raise RuntimeError(f"Unknown scope kind for {_concept.code}")
    if _concept.status not in {"active", "deprecated"}:
        raise RuntimeError(f"Unknown concept status for {_concept.code}")
    if (_concept.status == "deprecated") != (_concept.deprecated_at is not None):
        raise RuntimeError(f"Inconsistent deprecation for {_concept.code}")
    if _concept.parent_code is not None and _concept.parent_code not in CONCEPT_BY_CODE:
        raise RuntimeError(f"Unresolvable parent code for {_concept.code}")
    if _concept.default_unit is not None and _concept.default_unit not in CANONICAL_UNITS:
        raise RuntimeError(f"Unknown default unit for {_concept.code}")
    if len(_concept.code) > 100 or not _concept.code.strip():
        raise RuntimeError(f"Invalid concept code length for {_concept.code}")


def resolve_concept(code: str) -> ScopeConcept | None:
    """Exact code lookup. Deprecated codes remain resolvable."""
    return CONCEPT_BY_CODE.get(code)


def resolve_alias(term: str) -> ScopeConcept | None:
    """Exact normalized alias lookup. No fuzzy matching, no embeddings.

    An ambiguous or unknown term returns ``None``; it is never silently
    mapped onto a nearby concept.
    """
    code = ALIAS_TO_CODE.get(_normalize(term))
    return CONCEPT_BY_CODE.get(code) if code else None


def concept_payload(concept: ScopeConcept, *, include_aliases: bool = True) -> dict:
    return {
        "code": concept.code,
        "name": concept.name,
        "category": concept.category,
        "category_label": CATEGORY_LABELS[concept.category],
        "scope_kind": concept.scope_kind,
        "scope_kind_label": SCOPE_KIND_LABELS[concept.scope_kind],
        "description": concept.description,
        "parent_code": concept.parent_code,
        "default_unit": concept.default_unit,
        "status": concept.status,
        "deprecated_at": concept.deprecated_at,
        "aliases": list(concept.aliases) if include_aliases else [],
    }


def search_concepts(
    *,
    category: str | None = None,
    scope_kind: str | None = None,
    search: str = "",
    include_deprecated: bool = False,
    limit: int = 100,
) -> list[ScopeConcept]:
    """Deterministic bounded taxonomy search ordered by category then code."""
    normalized_search = _normalize(search)
    results = []
    for concept in CONCEPTS:
        if not include_deprecated and concept.status != "active":
            continue
        if category is not None and concept.category != category:
            continue
        if scope_kind is not None and concept.scope_kind != scope_kind:
            continue
        if normalized_search:
            haystack = (
                _normalize(concept.name),
                _normalize(concept.code),
                *(_normalize(alias) for alias in concept.aliases),
            )
            if not any(normalized_search in item for item in haystack):
                continue
        results.append(concept)
    results.sort(key=lambda item: (SCOPE_CATEGORIES.index(item.category), item.code))
    return results[:limit]
