"""Reproducible Metroville network and demonstration fixtures."""

from __future__ import annotations

from backend.database.repository import commit, execute, record_event, scalar


def seed_demo(db, reset: bool = False) -> None:
    if not reset and scalar(db, "SELECT COUNT(*) FROM locations"):
        return
    if reset:
        execute(db, "PRAGMA defer_foreign_keys = ON")
        for table in (
            "dispatch_records", "hospital_allocations", "evacuation_runs", "benchmark_runs",
            "algorithm_runs", "simulation_events", "incidents", "ambulances", "hospitals",
            "shelters", "roads", "locations",
        ):
            execute(db, f"DELETE FROM {table}")
        execute(db, "DELETE FROM sqlite_sequence")
    for r in range(6):
        for c in range(6):
            number = r * 6 + c + 1
            location_id = f"M{number:02d}"
            if number in (2, 8, 14, 20, 26, 32):
                kind = "hospital"
            elif number in (4, 10, 22, 28, 34, 36):
                kind = "shelter"
            elif number in (1, 19, 31):
                kind = "ambulance_station"
            elif number == 13:
                kind = "fire_station"
            elif number == 24:
                kind = "police_station"
            elif number in (3, 5, 9, 15, 17, 21, 25, 27, 33, 35):
                kind = "residential"
            else:
                kind = "intersection"
            execute(db,
                "INSERT INTO locations(id,name,kind,latitude,longitude) VALUES(?,?,?,?,?)",
                (location_id, f"{kind.replace('_', ' ').title()} {number:02d}", kind,
                 37.760 + r * 0.008, -122.470 + c * 0.010),
            )
    road_count = 0
    for r in range(6):
        for c in range(6):
            source = r * 6 + c + 1
            for dr, dc in ((0, 1), (1, 0)):
                nr, nc = r + dr, c + dc
                if nr >= 6 or nc >= 6:
                    continue
                target = nr * 6 + nc + 1
                distance = 1.1 + ((source * 7 + target * 3) % 9) / 10
                capacity = 90 + ((source * 13 + target * 7) % 8) * 25
                for start, end in ((source, target), (target, source)):
                    road_count += 1
                    minutes = 1.8 + ((start * 11 + end * 5) % 10) / 10
                    execute(db,
                        """INSERT INTO roads(source_id,target_id,distance_km,travel_minutes,
                           evacuation_capacity,infrastructure_cost) VALUES(?,?,?,?,?,?)""",
                        (f"M{start:02d}", f"M{end:02d}", distance, minutes, capacity,
                         round(distance * (1.0 + ((start + end) % 5) / 10), 2)),
                    )
    for index, location in enumerate(("M01", "M19", "M31", "M13", "M07", "M25", "M33", "M03"), start=1):
        execute(db,
            "INSERT INTO ambulances(id,location_id,status,capabilities) VALUES(?,?,?,?)",
            (f"AMB-{index:02d}", location, "available", "general,trauma" if index % 2 else "general"),
        )
    for index, location in enumerate(("M02", "M08", "M14", "M20", "M26", "M32"), start=1):
        execute(db,
            "INSERT INTO hospitals(id,name,location_id,total_beds,occupied_beds,specialties,accepting) VALUES(?,?,?,?,?,?,1)",
            (f"H-{index:02d}", f"Metroville Medical Center {index}", location, 50 + index * 10,
             12 + index * 4, "general,trauma" if index % 2 else "general,cardiac"),
        )
    for index, location in enumerate(("M04", "M10", "M22", "M28", "M34", "M36"), start=1):
        execute(db, "INSERT INTO shelters(id,name,location_id,capacity) VALUES(?,?,?,?)",
                   (f"S-{index:02d}", f"Community Shelter {index}", location, 180 + index * 40))
    execute(db,
        """INSERT INTO incidents(location_id,incident_type,severity,required_unit,required_specialty,
           description,status) VALUES('M17','Traffic collision','High','ambulance','trauma',
           'Two-vehicle collision; simulated training incident','Pending')"""
    )
    execute(db,
        """INSERT INTO incidents(location_id,incident_type,severity,required_unit,description,status)
           VALUES('M29','Structure fire','Medium','fire','Drill scenario; no real emergency','Pending')"""
    )
    record_event(db, "system", f"Metroville demo network seeded ({road_count} directed roads)")
    commit(db)
