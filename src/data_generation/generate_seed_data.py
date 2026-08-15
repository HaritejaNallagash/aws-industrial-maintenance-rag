"""Generate realistic industrial maintenance source documents.

The generated corpus represents a packaging plant with fillers, conveyors,
carton sealers, palletizers, pumps, and inspection stations. The output files
are plain-text operational documents so the raw layer looks and feels like
real-world maintenance knowledge rather than already-normalized JSON.

Each text file includes:

1. a compact metadata header that a parser can reliably read
2. a free-form body written as natural language operating content
"""

import argparse
import json
from pathlib import Path
from typing import Dict, Iterable, List


SITE_ID = "PLANT-ATL-01"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", required=True, help="Directory where source text files are written.")
    parser.add_argument("--question-file", required=True, help="Path where known validation questions are written.")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    cleanup_generated_source_directory(output_dir)

    documents = list(generate_documents())
    for document in documents:
        path = output_dir / ("%s.txt" % document["document_id"])
        path.write_text(render_text_document(document), encoding="utf-8")

    question_path = Path(args.question_file)
    question_path.parent.mkdir(parents=True, exist_ok=True)
    question_path.write_text(json.dumps(generate_questions(), indent=2), encoding="utf-8")

    print("Wrote %s source documents to %s" % (len(documents), output_dir))


def generate_documents() -> Iterable[Dict]:
    """Yield the complete source corpus."""
    yield _doc(
        "SOP-FILL-203-PRESSURE-LOSS",
        "FILL-203 intermittent pressure loss troubleshooting procedure",
        "troubleshooting_guide",
        "FILL-203",
        "LINE-3",
        "medium",
        [
            "Symptom: filler FILL-203 reports intermittent pressure loss during the high-speed bottle fill cycle. Operators usually see pressure drift between 48 and 63 PSI, followed by short-fill rejects at the checkweigher.",
            "Immediate containment: place the filler in controlled stop, divert affected bottles to hold, and verify the guard doors remain latched. Do not bypass the pressure interlock while production is active.",
            "Inspection sequence: check the inlet regulator for oscillation, inspect the VX-220 valve assembly for seal swelling, verify that the air preparation bowl is not saturated, and confirm that the pressure transducer PT-203A cable is fully seated.",
            "Known fix from reliability engineering: if pressure recovers after cycling the air preparation drain, replace the coalescing filter element and inspect the drain float. If the pressure drops only when nozzle bank B actuates, replace valve assembly VX-220-B and retest the bank.",
            "Escalation: if the pressure reading remains unstable after regulator and valve checks, open a controls work order to test analog input card AI-17 and compare PT-203A against a calibrated mechanical gauge.",
        ],
    )
    yield _doc(
        "INC-2026-0142-FILL-203",
        "Incident report for repeated FILL-203 short-fill rejects",
        "incident_report",
        "FILL-203",
        "LINE-3",
        "high",
        [
            "During the night shift on 2026-02-17, Line 3 produced 418 short-fill rejects in 22 minutes. The first alarm was FILL-203-PRES-LOW, followed by intermittent recovery without operator reset.",
            "The maintenance technician found water in the compressed-air bowl and a swollen seal on the VX-220-B valve assembly. The regulator diaphragm passed leakdown testing, and PT-203A matched a calibrated gauge within 1.5 PSI.",
            "Corrective action: the team replaced the coalescing filter element, drained the air header low point, installed valve assembly VX-220-B revision C, and ran a 30-minute verification at 240 bottles per minute with zero short fills.",
            "Preventive action: the air preparation bowl on FILL-203 must be inspected at the start of each shift during high-humidity months. Reliability engineering added a weekly compressed-air moisture trend review for Line 3.",
        ],
    )
    yield _doc(
        "PM-FILL-203-AIR-PREP",
        "Preventive maintenance standard for FILL-203 air preparation assembly",
        "preventive_maintenance",
        "FILL-203",
        "LINE-3",
        "medium",
        [
            "Scope: this standard covers the regulator, coalescing filter, drain float, pressure transducer PT-203A, and nozzle-bank valve assemblies for filler FILL-203.",
            "Weekly checks: inspect the air bowl for water accumulation, verify the drain float moves freely, confirm regulator setpoint is 58 PSI under load, and inspect valve assemblies VX-220-A through VX-220-D for audible leakage.",
            "Monthly checks: replace the coalescing filter element if the differential indicator is red or if any moisture is found downstream of the filter. Record the regulator loaded and unloaded pressure in the maintenance log.",
            "Acceptance criteria: pressure must remain between 56 and 60 PSI during a simulated fill cycle. The pressure trace may not show more than 3 PSI peak-to-peak oscillation while any nozzle bank is actuating.",
        ],
    )
    yield _doc(
        "PART-VX-220-VALVE-ASSEMBLY",
        "Spare parts specification for VX-220 pneumatic valve assembly",
        "spare_part_catalog",
        "FILL-203",
        "LINE-3",
        "low",
        [
            "Part: VX-220 pneumatic valve assembly. Approved revision for FILL-203 is VX-220 revision C. Revision B is allowed only as an emergency temporary replacement for no more than 72 operating hours.",
            "Compatible positions: nozzle-bank valves VX-220-A, VX-220-B, VX-220-C, and VX-220-D. The same assembly is not approved for the carton sealer adhesive solenoid manifold.",
            "Required consumables: food-grade pneumatic seal kit SK-220-C, thread sealant TS-19, and replacement push-to-connect fittings if tubing shows scoring.",
            "Post-installation check: run manual actuation for the affected nozzle bank, verify no audible leakage, and perform a 10-minute pressure stability test before returning the filler to production.",
        ],
    )
    yield _doc(
        "SOP-PAL-410-LOCKOUT",
        "Lockout procedure before servicing palletizer PAL-410 lift motor",
        "safety_procedure",
        "PAL-410",
        "LINE-4",
        "critical",
        [
            "Before servicing the PAL-410 lift motor, stop the palletizer through the operator panel and wait until the carriage is fully lowered onto mechanical stops.",
            "Apply lockout to the main electrical disconnect DS-PAL-410, the 480V motor starter cabinet, and the pneumatic dump valve feeding the clamp assembly. Verify zero energy with a properly rated meter.",
            "Stored energy warning: the lift carriage can drift if the brake is released without support. Install the red mechanical safety pins on both carriage rails before removing the motor coupling guard.",
            "Return-to-service check: remove tools, verify guards are installed, remove locks according to the site energy-control policy, jog the lift in maintenance mode, and observe one empty pallet cycle.",
        ],
    )
    yield _doc(
        "MAN-CONV-118-BELT-TRACKING",
        "Conveyor CONV-118 belt tracking and tension manual section",
        "equipment_manual",
        "CONV-118",
        "LINE-2",
        "medium",
        [
            "CONV-118 transfers filled cases from the case erector to the checkweigher. Belt tracking problems usually appear as left-edge fray, side rail rub marks, or product skew before the checkweigher infeed.",
            "Tracking adjustment: verify the frame is square, clean debris from the tail pulley, and adjust the take-up bolts in quarter-turn increments. Run the belt for five minutes between adjustments.",
            "Tension target: the belt should deflect 14 to 18 mm at midspan under moderate thumb pressure. Over-tension increases bearing temperature and can cause motor overload trips.",
            "Do not compensate for damaged lacing by over-tightening the belt. Replace the belt if more than two lacing hooks are missing or if the belt edge has exposed reinforcement cords.",
        ],
    )
    yield _doc(
        "INC-2026-0109-CONV-118",
        "Incident report for CONV-118 motor overload trips",
        "incident_report",
        "CONV-118",
        "LINE-2",
        "medium",
        [
            "CONV-118 tripped on motor overload three times during first shift. The overload reset succeeded, but the motor casing temperature reached 78 C after the third restart.",
            "Maintenance found belt tension above specification and dried adhesive buildup on the tail pulley. The belt was tracking against the left side rail, causing case skew and elevated motor load.",
            "Corrective action: cleaned the tail pulley, reset take-up bolts to achieve 16 mm belt deflection, replaced damaged side rail wear strip, and observed the conveyor for 45 minutes without overload.",
            "Follow-up: add CONV-118 tail pulley cleaning to the Friday sanitation handoff when adhesive transfer is reported by quality inspection.",
        ],
    )
    yield _doc(
        "SOP-CASE-330-ADHESIVE-TEMP",
        "Carton sealer CASE-330 adhesive temperature troubleshooting",
        "troubleshooting_guide",
        "CASE-330",
        "LINE-3",
        "medium",
        [
            "CASE-330 creates weak carton seals when adhesive temperature falls below 168 C at the nozzle block. Quality may report open flaps or stringing adhesive at the compression belt exit.",
            "Inspection sequence: verify tank temperature, hose temperature, nozzle block temperature, adhesive level, and compression belt pressure. A low nozzle temperature with normal tank temperature usually indicates a hose heater fault.",
            "Known fault code ADH-TMP-17 means the nozzle block thermistor is out of range. Inspect connector J17 for adhesive contamination before replacing the thermistor.",
            "Return-to-service: purge the nozzle block after temperature recovery and validate seal strength on ten cartons from each lane.",
        ],
    )
    yield _doc(
        "PART-CASE-330-THERMISTOR",
        "CASE-330 nozzle block thermistor replacement part",
        "spare_part_catalog",
        "CASE-330",
        "LINE-3",
        "low",
        [
            "Part: NB-THE-17 nozzle block thermistor for CASE-330 adhesive system. The part includes a stainless probe, high-temperature lead, and connector keyed for J17.",
            "Compatibility: approved for CASE-330 nozzle block positions one through four. It is not compatible with the tank RTD or hose heater sensor.",
            "Installation note: clean adhesive residue from connector J17, route the lead away from the compression belt, and confirm the controller reads ambient temperature before heating the system.",
        ],
    )
    yield _doc(
        "SOP-VIS-520-REJECT-SPIKE",
        "Vision station VIS-520 false reject spike response",
        "troubleshooting_guide",
        "VIS-520",
        "LINE-5",
        "medium",
        [
            "VIS-520 may reject acceptable labels when the camera lens has condensation, the strobe intensity drifts, or the label presentation angle changes at the infeed guide.",
            "Response sequence: clean the lens with approved wipes, inspect the strobe cable, verify recipe code against the production order, and run the golden-sample validation card.",
            "If false rejects continue after cleaning, compare the current brightness histogram to the reference image. A shift greater than 12 percent requires strobe recalibration by controls.",
            "Do not lower inspection sensitivity without quality approval. Record the reject count before and after each action.",
        ],
    )
    yield _doc(
        "PM-PUMP-707-SEAL",
        "CIP pump PUMP-707 seal inspection procedure",
        "preventive_maintenance",
        "PUMP-707",
        "UTILITY",
        "medium",
        [
            "PUMP-707 circulates cleaning solution through the filler clean-in-place loop. A failing mechanical seal can contaminate the motor base and reduce CIP flow rate.",
            "Inspection: lock out the pump starter, verify zero pressure, inspect the seal weep port, check motor base staining, and rotate the shaft by hand for roughness.",
            "Replacement trigger: replace the seal if the weep port drips more than one drop per minute, if caustic residue is visible on the base, or if vibration exceeds the route limit.",
            "After replacement, run a water flush, confirm no leakage for 15 minutes, and document the seal lot number in the maintenance record.",
        ],
    )
    yield _doc(
        "ALARM-CODE-REFERENCE",
        "Common maintenance alarm code reference",
        "alarm_reference",
        "MULTI",
        "ALL",
        "low",
        [
            "FILL-203-PRES-LOW: filler pressure below operating threshold. Check compressed-air moisture, inlet regulator stability, PT-203A signal integrity, and VX-220 valve assemblies.",
            "ADH-TMP-17: carton sealer nozzle block thermistor out of range. Check connector J17 for adhesive contamination and verify the nozzle block thermistor before replacing heater components.",
            "CONV-118-MTR-OL: conveyor motor overload. Check belt tension, tail pulley buildup, bearing temperature, and side rail contact.",
            "VIS-520-REJ-HIGH: vision reject rate above threshold. Check lens condition, strobe output, recipe code, and label guide position.",
        ],
    )


def generate_questions() -> List[Dict]:
    """Known questions used by people and automated smoke checks."""
    return [
        {
            "question": "What should a technician inspect when filler FILL-203 reports intermittent pressure loss?",
            "filters": {"equipment_id": "FILL-203"},
        },
        {
            "question": "Which part replaces the VX-220-B valve on FILL-203?",
            "filters": {"document_type": "spare_part_catalog"},
        },
        {
            "question": "What lockout steps apply before servicing palletizer PAL-410 lift motor?",
            "filters": {"equipment_id": "PAL-410"},
        },
        {
            "question": "Why did CONV-118 overload and how was it corrected?",
            "filters": {"equipment_id": "CONV-118"},
        },
    ]


def _doc(
    document_id: str,
    title: str,
    document_type: str,
    equipment_id: str,
    production_line: str,
    severity: str,
    paragraphs: List[str],
) -> Dict:
    return {
        "document_id": document_id,
        "title": title,
        "body": "\n\n".join(paragraphs),
        "metadata": {
            "site_id": SITE_ID,
            "production_line": production_line,
            "equipment_id": equipment_id,
            "document_type": document_type,
            "severity": severity,
            "effective_date": "2026-03-01",
            "source_system": "maintenance-engineering",
        },
    }


def render_text_document(document: Dict) -> str:
    """Render one source record as a plain-text document with front matter.

    The front matter keeps metadata human-readable and machine-parseable. The
    body remains unstructured text, which is what the chunker and embedding
    pipeline actually use for retrieval.
    """
    metadata = document["metadata"]
    header_lines = [
        "---",
        "document_id: %s" % document["document_id"],
        "title: %s" % document["title"],
        "site_id: %s" % metadata["site_id"],
        "production_line: %s" % metadata["production_line"],
        "equipment_id: %s" % metadata["equipment_id"],
        "document_type: %s" % metadata["document_type"],
        "severity: %s" % metadata["severity"],
        "effective_date: %s" % metadata["effective_date"],
        "source_system: %s" % metadata["source_system"],
        "---",
        "",
    ]
    return "\n".join(header_lines) + document["body"] + "\n"


def cleanup_generated_source_directory(output_dir: Path) -> None:
    """Remove stale generated source files from earlier format revisions.

    This keeps the generated corpus deterministic and avoids mixing the current
    `.txt` source format with older `.json` source documents in the same folder.
    """
    for pattern in ("*.txt", "*.json"):
        for path in output_dir.glob(pattern):
            path.unlink()


if __name__ == "__main__":
    main()
