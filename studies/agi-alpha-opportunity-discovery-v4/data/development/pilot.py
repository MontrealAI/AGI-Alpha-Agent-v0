"""One-part development pilot on unchanged NIST Plate artifacts.

This is an evidence audit, not a part release or measurement qualification.
Selected example IDs are disclosed development choices, not hidden confirmation.
Uses actual OpenCascade geometry; text indexing below only locates source records.
"""
from pathlib import Path
from collections import Counter
from itertools import permutations
import hashlib, json, platform, re, time
import numpy as np
from lxml import etree
import cadquery as cq
import OCP
from OCP.BRepAdaptor import BRepAdaptor_Surface
from OCP.GeomAbs import GeomAbs_Cylinder

BASE = Path(__file__).resolve().parent
INP = BASE / 'inputs'
NS = {'q': 'http://qifstandards.org/xsd/qif2'}
RDF = '{http://www.w3.org/1999/02/22-rdf-syntax-ns#}'
QOWL = 'http://www.nist.gov/QIF_ontology#'

def txt(e, path, default=None):
    return e.findtext(path, default=default, namespaces=NS)

def name(e):
    return etree.QName(e).localname

def read_qif(file):
    tree = etree.parse(str(INP / file))
    ids = {e.get('id'): e for e in tree.iter() if e.get('id')}
    chars = {}
    for item in tree.findall('q:Characteristics/q:CharacteristicItems/*', NS):
        nominal = ids[txt(item, 'q:CharacteristicNominalId')]
        definition = ids[txt(nominal, 'q:CharacteristicDefinitionId')]
        target = txt(nominal, 'q:TargetValue')
        target = float(target) if target is not None else None
        low, high = txt(definition, 'q:Tolerance/q:MinValue'), txt(definition, 'q:Tolerance/q:MaxValue')
        absolute = txt(definition, 'q:Tolerance/q:DefinedAsLimit')
        interval = None
        if low is not None and high is not None and absolute in ('true', 'false'):
            offset = 0 if absolute == 'true' else target
            if offset is not None:
                interval = [float(low) + offset, float(high) + offset]
        chars[item.get('id')] = {
            'item_id': item.get('id'), 'name': txt(item, 'q:Name'),
            'kind': name(item).replace('CharacteristicItem', ''),
            'nominal_id': nominal.get('id'), 'definition_id': definition.get('id'),
            'target': target, 'interval': interval, 'defined_as_limit': absolute,
            'material_condition_literal': txt(definition, 'q:MaterialCondition'),
            'tolerance_value_literal': txt(definition, 'q:ToleranceValue'),
            'analysis_mode_literal': txt(nominal, 'q:AnalysisMode'),
            'features': [e.text for e in item.findall('q:FeatureItemIds/q:Id', NS)],
            'actuals': []}
    for e in tree.findall('.//q:CharacteristicActuals/*', NS):
        key = txt(e, 'q:CharacteristicItemId')
        if key in chars:
            value = txt(e, 'q:Value')
            chars[key]['actuals'].append({'id': e.get('id'), 'value': float(value) if value else None,
                'status': txt(e, 'q:Status/q:CharacteristicStatusEnum'),
                'feature_actual_ids': [x.text for x in e.findall('q:FeatureActualIds/q:Id', NS)]})
    unit = tree.find('q:FileUnits/q:PrimaryUnits/q:LinearUnit', NS)
    return tree, ids, chars, None if unit is None else {
        'name': txt(unit, 'q:UnitName'), 'si': txt(unit, 'q:SIUnitName'),
        'factor': txt(unit, 'q:UnitConversion/q:Factor')}

def main():
    started = time.perf_counter()
    manifest = json.loads((BASE / 'input_manifest.json').read_text())
    for row in manifest:
        assert hashlib.sha256((INP / row['file']).read_bytes()).hexdigest() == row['sha256']
    fair_tree, fair_ids, fair, fair_unit = read_qif('Plate_FAIR.qif')
    inc_tree, inc_ids, incoming, incoming_unit = read_qif('Plate_incoming.qif')
    shape = cq.importers.importStep(str(INP / 'Plate_AP242.STP')).val()
    faces = shape.Faces()
    cylinders = []
    for i, face in enumerate(faces):
        adaptor = BRepAdaptor_Surface(face.wrapped)
        if adaptor.GetType() == GeomAbs_Cylinder:
            cyl = adaptor.Cylinder(); axis = cyl.Axis(); box = face.BoundingBox()
            cylinders.append({'face_index': i, 'radius': cyl.Radius(),
                'location': list(axis.Location().Coord()), 'direction': list(axis.Direction().Coord()),
                'area': face.Area(), 'z_extent': [box.zmin, box.zmax]})
    matches = []
    # No invented pair labels: candidate geometry comes from source axes/radii.
    # The equal-coordinate-frame assumption is explicit and residual-tested here.
    for f in inc_tree.findall('q:Features/q:FeatureItems/*', NS):
        if name(f) != 'CylinderFeatureItem':
            continue
        nominal = inc_ids[txt(f, 'q:FeatureNominalId')]
        definition = inc_ids[txt(nominal, 'q:FeatureDefinitionId')]
        location = np.fromstring(txt(nominal, 'q:Axis/q:AxisPoint'), sep=' ')
        direction = np.fromstring(txt(nominal, 'q:Axis/q:Direction'), sep=' ')
        direction /= np.linalg.norm(direction)
        diameter = float(txt(definition, 'q:Diameter'))
        found = []
        for c in cylinders:
            axis = np.asarray(c['direction'])
            distance = float(np.linalg.norm(np.cross(location - np.asarray(c['location']), axis)))
            angle_residual = float(1 - abs(direction @ axis))
            radius_residual = abs(diameter / 2 - c['radius'])
            if distance < 1e-5 and angle_residual < 1e-10 and radius_residual < 1e-5:
                found.append({'face_index': c['face_index'], 'axis_distance_mm': distance,
                              'direction_residual': angle_residual, 'radius_residual_mm': radius_residual})
        matches.append({'feature_item_id': f.get('id'), 'feature_name': txt(f, 'q:FeatureName'),
            'feature_nominal_id': nominal.get('id'), 'feature_definition_id': definition.get('id'),
            'axis_point': location.tolist(), 'axis_direction': direction.tolist(),
            'diameter': diameter, 'candidate_faces': found})

    # Disclosed demonstration trace: first actual of incoming DIAMETER7.
    requirement = incoming['101']
    actual = next(x for x in requirement['actuals'] if x['id'] == '102')
    feat_actual = inc_ids[actual['feature_actual_ids'][0]]
    feat_item_id = txt(feat_actual, 'q:FeatureItemId')
    geom_match = next(x for x in matches if x['feature_item_id'] == feat_item_id)
    face = next(x for x in cylinders if x['face_index'] == geom_match['candidate_faces'][0]['face_index'])
    measurement_set = next(x for x in inc_ids['102'].iterancestors() if name(x) == 'MeasurementResults')
    component_id = txt(measurement_set, 'q:ActualComponentIds/q:Id')
    # Reuse the supplied reference graph's existing QIF representation as E evidence.
    owl = etree.parse(str(INP / 'Plate_integrated.owl'))
    ref_assertions = []
    for e in owl.getroot():
        if not isinstance(e.tag, str):
            continue
        id_node = e.find('{' + QOWL + '}_id')
        if id_node is not None and id_node.text in {'99', '100', '101', '95', '96', '97', '98', '102'}:
            ref_assertions.append({'uri': e.get(RDF + 'about'), 'qif_id': id_node.text,
                'assertions': {name(x): x.get(RDF + 'resource') or x.text for x in e}})
    # STEP text is indexed only for verifiable citations, not geometry interpretation.
    records = {i: v for i, v in re.findall(r'#(\d+)\s*=\s*(.*?);', (INP / 'Plate_AP242.STP').read_text(), re.S)}
    step_records = {i: records[i] for i in ['8', '7265', '7266', '7267', '7268', '7269', '7281']}
    trace = {'scope': 'one incoming diameter obligation, not overall part acceptance',
        'requirement': {k:v for k,v in requirement.items() if k != 'actuals'}, 'actual': actual,
        'feature_actual_id': feat_actual.get('id'), 'feature_actual_diameter': float(txt(feat_actual, 'q:Diameter')),
        'geometry': geom_match, 'cad_surface': face, 'step_records': step_records,
        'reference_graph_assertions': ref_assertions, 'measurement_result_id': measurement_set.get('id'),
        'component_id': component_id, 'serial': txt(inc_ids[component_id], 'q:SerialNumber'),
        'overall_inspection_status': txt(measurement_set, 'q:InspectionStatus/q:InspectionStatusEnum'),
        'numeric_requirement_satisfied': requirement['interval'][0] <= actual['value'] <= requirement['interval'][1]}

    normalize = lambda text: re.sub(r'\s+', '', text or '').upper()
    label_pairs = []
    for a in fair.values():
        for b in incoming.values():
            if normalize(a['name']) == normalize(b['name']) and a['target'] and b['target']:
                label_pairs.append({'fair_id': a['item_id'], 'incoming_id': b['item_id'],
                    'label': normalize(a['name']), 'fair_nominal': a['target'], 'incoming_nominal': b['target'],
                    'required_common_unit_scale': b['target'] / a['target']})

    # Pure numeric countermodel; intentionally not an observed measurement.
    a, b = fair['110'], incoming['169']
    counterexample = {'fair_id': '110', 'incoming_id': '169',
        'scope': 'candidate same-distance interpretation under explicitly common units; identity is unproved',
        'fair_interval': a['interval'], 'incoming_interval': b['interval'],
        'constructed_value': 71.38,
        'fair_numeric_pass': a['interval'][0] <= 71.38 <= a['interval'][1],
        'incoming_numeric_pass': b['interval'][0] <= 71.38 <= b['interval'][1],
        'observed_measurement': False}

    candidate_family = [x for x in fair.values() if x['kind'] == 'Diameter' and x['target'] == requirement['target']]
    values = [y['value'] for x in candidate_family for y in x['actuals']]
    destination = requirement['interval']
    permutations_checked = list(permutations([x['item_id'] for x in candidate_family]))
    inclusion = all(destination[0] <= x['interval'][0] <= x['interval'][1] <= destination[1] for x in candidate_family)
    schema = etree.parse(str(BASE / 'QIF_2_1_Units.xsd'))
    xns = {'xs':'http://www.w3.org/2001/XMLSchema'}
    unit_docs = {}
    for kind in ['LinearValueType','ActualLinearValueType']:
        node = schema.find(f"xs:complexType[@name='{kind}']/xs:annotation/xs:documentation", xns)
        unit_docs[kind] = ' '.join(node.itertext()).strip()
    fair_unit_overrides = [{'element':name(e),'attribute':k,'value':v}
        for e in fair_tree.iter() for k,v in e.attrib.items() if 'unit' in k.lower()]
    assert all('meters if not' in v for v in unit_docs.values())
    certificate = {'scope': 'counterfactual numeric certificate AFTER authorized FAIR millimeter metadata repair; NOT admitted physical reuse',
        'current_formal_default': 'meters', 'admitted_cross_provider_reuse': False,
        'fair_candidate_item_ids': [x['item_id'] for x in candidate_family],
        'fair_candidate_intervals': [x['interval'] for x in candidate_family],
        'incoming_characteristic_item': '101', 'incoming_interval': destination,
        'all_source_intervals_subset_of_destination': inclusion,
        'recorded_value_count': len(values), 'recorded_value_min': min(values), 'recorded_value_max': max(values),
        'all_recorded_values_satisfy_destination_numeric_interval': all(destination[0] <= x <= destination[1] for x in values),
        'number_of_candidate_feature_permutations': len(permutations_checked),
        'permutations': permutations_checked,
        'individual_feature_permutation_needed_for_family_all_pass': False,
        'prerequisites_not_established': ['authorized correction confirming intended FAIR millimeter units despite formal meter default',
            'same complete design/inspection requirement identity or accepted requalification',
            'set identity: three FAIR characteristics cover the same three intended diameter features',
            'specimen/lot identity and coverage between providers', 'measurement adequacy and authorized acceptance'],
        'cad_nominal_three_diameter_faces': [c['face_index'] for c in cylinders if abs(c['radius']-1.5)<1e-8]}

    checks = {
        'source_hashes_unchanged': True,
        'valid_solid': shape.isValid() and len(shape.Solids()) == 1,
        'trace_unique_geometry_candidate': len(geom_match['candidate_faces']) == 1,
        'trace_item_matches_feature_actual': feat_item_id in requirement['features'],
        'trace_value_equals_feature_diameter': actual['value'] == trace['feature_actual_diameter'],
        'trace_numeric_pass_matches_record': trace['numeric_requirement_satisfied'] and actual['status'] == 'PASS',
        'trace_does_not_release_failed_part': trace['overall_inspection_status'] == 'FAIL',
        'reference_contains_existing_item_101': any(x['qif_id']=='101' for x in ref_assertions),
        'label_join_inconsistent_under_uniform_scale': len({round(x['required_common_unit_scale'],8) for x in label_pairs}) > 1,
        'countermodel_rejects_equal_intervals': counterexample['fair_numeric_pass'] and not counterexample['incoming_numeric_pass'],
        'conditional_numeric_certificate_after_unit_repair': inclusion and certificate['all_recorded_values_satisfy_destination_numeric_interval'],
        'exact_schema_default_and_absent_overrides': fair_unit is None and not fair_unit_overrides,
        'three_candidate_family_and_cad_features': len(candidate_family)==len(certificate['cad_nominal_three_diameter_faces'])==3}
    receipt = {'status':'development pilot; not prospective confirmation or independent customer acceptance',
        'versions': {'python': platform.python_version(), 'cadquery':cq.__version__, 'OCP':OCP.__version__},
        'input_manifest':manifest, 'units':{'incoming':incoming_unit,'FAIR_explicit_file_units':fair_unit,
            'FAIR_per_value_unit_attributes':fair_unit_overrides,'FAIR_formal_default':'meter',
            'FAIR_candidate_values_as_formal_millimeters':[1000*min(values),1000*max(values)],
            'schema_source':'https://qifstandards.org/wp-content/uploads/2015/03/QIF-2.1.zip',
            'schema_member':'QIF_2.1_XMLSchemaFiles.zip/QIFLibrary/Units.xsd',
            'schema_sha256':hashlib.sha256((BASE/'QIF_2_1_Units.xsd').read_bytes()).hexdigest(),
            'schema_documentation':unit_docs},
        'cad':{'valid':shape.isValid(),'solids':len(shape.Solids()),'faces':len(faces),'edges':len(shape.Edges()),
               'surface_types':dict(Counter(f.geomType() for f in faces))},
        'cylindrical_feature_matches':matches, 'complete_trace':trace, 'label_join_diagnostics':label_pairs,
        'interval_countermodel':counterexample, 'conditional_reuse_certificate':certificate,
        'literal_semantic_conflicts':{'position':{'FAIR':fair['14']['material_condition_literal'],
                                                 'incoming':incoming['40']['material_condition_literal'],
                'interpretation':'different literals; authoritative semantic adjudication still required'},
            'perpendicularity_tolerance':{'FAIR':fair['11']['tolerance_value_literal'],
                'incoming':incoming['29']['tolerance_value_literal'],
                'interpretation':'sign discrepancy retained; no silent absolute-value correction'}},
        'mechanical_checks':checks, 'run_seconds':time.perf_counter()-started,
        'limits':['Plate only; no Box/Cover inspected during this pilot',
            'No full QIF XSD/GD&T standards conformance validation',
            'No current cross-provider physical equivalence or authority established',
            'No commercial cost advantage or new feasibility measured',
            'Reference graph reused as supplied; no graph-versus-library claim',
            'Common coordinate representation checked on this model; no universal registration method claimed']}
    assert all(checks.values()), checks
    (BASE/'pilot_receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps({'checks':checks,'seconds':receipt['run_seconds'],
        'cylindrical_features':len(matches),'with_candidates':sum(bool(x['candidate_faces']) for x in matches),
        'trace':{'qif_item':'101','actual':'102','value':actual['value'],'CAD_face':face['face_index']},
        'family':certificate},indent=2))

if __name__ == '__main__':
    main()
