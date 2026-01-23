#!/usr/bin/env python3
"""
Clean DevOps Shield SARIF exports for GitHub Code Scanning compatibility.

DevOps Shield exports SARIF with non-standard properties that GitHub rejects.
This script transforms the SARIF to strict 2.1.0 spec compliance.

Usage:
    python Clean-SarifForGitHub.py input.sarif [output.sarif]
    
If output is not specified, the input file is overwritten.
"""

import json
import sys
from pathlib import Path


# Non-standard properties to remove at any level
PROPERTIES_TO_REMOVE = {
    'sarifNodeKind',
    'propertyNames', 
    'tags',
    'moniker',
    'isBinaryRegion',
    'isLineColumnBasedTextRegion',
    'isOffsetBasedTextRegion',
}

# Level enum mapping (numeric to string)
LEVEL_MAP = {
    0: 'none',
    1: 'note',
    2: 'warning',
    3: 'error',
}

# Kind enum mapping (numeric to string)
KIND_MAP = {
    0: 'notApplicable',
    1: 'pass',
    2: 'fail',
    3: 'open',
    4: 'informational',
    5: 'review',
}

# BaselineState enum mapping (numeric to string)
BASELINE_STATE_MAP = {
    0: 'new',
    1: 'unchanged',
    2: 'updated',
    3: 'absent',
}


def clean_object(obj):
    """Recursively clean an object by removing non-standard properties."""
    if isinstance(obj, dict):
        # Remove non-standard properties
        cleaned = {k: clean_object(v) for k, v in obj.items() 
                   if k not in PROPERTIES_TO_REMOVE}
        # Remove None values, empty dicts, empty lists
        cleaned = {k: v for k, v in cleaned.items() 
                   if v is not None and v != {} and v != []}
        return cleaned
    elif isinstance(obj, list):
        return [clean_object(item) for item in obj if item is not None]
    else:
        return obj


def fix_level(level):
    """Convert numeric level to string enum."""
    if isinstance(level, int):
        return LEVEL_MAP.get(level, 'warning')
    elif isinstance(level, str) and level.lower() in ['none', 'note', 'warning', 'error']:
        return level.lower()
    return 'warning'


def fix_kind(kind):
    """Convert numeric kind to string enum."""
    if isinstance(kind, int):
        return KIND_MAP.get(kind, 'open')
    elif isinstance(kind, str):
        return kind.lower() if kind.lower() in KIND_MAP.values() else 'open'
    return 'open'


def fix_baseline_state(state):
    """Convert numeric baselineState to string enum."""
    if isinstance(state, int):
        return BASELINE_STATE_MAP.get(state, 'new')
    elif isinstance(state, str) and state.lower() in ['new', 'unchanged', 'updated', 'absent']:
        return state.lower()
    return None  # Remove if invalid


def clean_location(location):
    """Clean a location object."""
    if not isinstance(location, dict):
        return None
    
    cleaned = {}
    
    # Handle id - must be integer, remove if not
    if 'id' in location:
        if isinstance(location['id'], int) and location['id'] >= 0:
            cleaned['id'] = location['id']
        elif isinstance(location['id'], dict):
            # Skip BigInt-like objects
            pass
    
    # Clean physicalLocation
    if 'physicalLocation' in location:
        phys = location['physicalLocation']
        if isinstance(phys, dict):
            cleaned_phys = {}
            
            # Clean artifactLocation
            if 'artifactLocation' in phys:
                artifact = phys['artifactLocation']
                if isinstance(artifact, dict):
                    cleaned_artifact = {}
                    if 'uri' in artifact:
                        cleaned_artifact['uri'] = str(artifact['uri'])
                    if 'uriBaseId' in artifact and artifact['uriBaseId']:
                        cleaned_artifact['uriBaseId'] = str(artifact['uriBaseId'])
                    if 'index' in artifact and isinstance(artifact['index'], int) and artifact['index'] >= 0:
                        cleaned_artifact['index'] = artifact['index']
                    # Skip description - it has too many non-standard fields
                    if cleaned_artifact:
                        cleaned_phys['artifactLocation'] = cleaned_artifact
            
            # Clean region
            if 'region' in phys:
                region = phys['region']
                if isinstance(region, dict):
                    cleaned_region = {}
                    for key in ['startLine', 'startColumn', 'endLine', 'endColumn']:
                        if key in region and isinstance(region[key], int) and region[key] > 0:
                            cleaned_region[key] = region[key]
                    if cleaned_region:
                        cleaned_phys['region'] = cleaned_region
            
            if cleaned_phys:
                cleaned['physicalLocation'] = cleaned_phys
    
    # Clean logicalLocations
    if 'logicalLocations' in location:
        logical_locs = location['logicalLocations']
        if isinstance(logical_locs, list):
            cleaned_logical = []
            for ll in logical_locs:
                if isinstance(ll, dict):
                    cleaned_ll = {}
                    if 'name' in ll:
                        cleaned_ll['name'] = str(ll['name'])
                    if 'fullyQualifiedName' in ll:
                        cleaned_ll['fullyQualifiedName'] = str(ll['fullyQualifiedName'])
                    if 'kind' in ll:
                        cleaned_ll['kind'] = str(ll['kind'])
                    if cleaned_ll:
                        cleaned_logical.append(cleaned_ll)
            if cleaned_logical:
                cleaned['logicalLocations'] = cleaned_logical
    
    # Clean message
    if 'message' in location:
        msg = location['message']
        if isinstance(msg, dict) and 'text' in msg:
            cleaned['message'] = {'text': str(msg['text'])}
    
    return cleaned if cleaned else None


def clean_result(result):
    """Clean a result object."""
    if not isinstance(result, dict):
        return None
    
    cleaned = {}
    
    # Required: ruleId
    if 'ruleId' in result:
        cleaned['ruleId'] = str(result['ruleId'])
    
    # Optional: ruleIndex
    if 'ruleIndex' in result and isinstance(result['ruleIndex'], int) and result['ruleIndex'] >= 0:
        cleaned['ruleIndex'] = result['ruleIndex']
    
    # Fix level
    if 'level' in result:
        cleaned['level'] = fix_level(result['level'])
    
    # Fix kind
    if 'kind' in result:
        cleaned['kind'] = fix_kind(result['kind'])
    
    # Clean message
    if 'message' in result:
        msg = result['message']
        if isinstance(msg, dict) and 'text' in msg:
            cleaned['message'] = {'text': str(msg['text'])}
            if 'markdown' in msg and msg['markdown']:
                cleaned['message']['markdown'] = str(msg['markdown'])
    
    # Clean locations
    if 'locations' in result:
        locs = result['locations']
        if isinstance(locs, list):
            cleaned_locs = []
            for loc in locs:
                cleaned_loc = clean_location(loc)
                if cleaned_loc:
                    cleaned_locs.append(cleaned_loc)
            if cleaned_locs:
                cleaned['locations'] = cleaned_locs
    
    # Handle fingerprints (keep as-is if valid)
    if 'fingerprints' in result and isinstance(result['fingerprints'], dict):
        cleaned['fingerprints'] = {k: str(v) for k, v in result['fingerprints'].items() if v}
    if 'partialFingerprints' in result and isinstance(result['partialFingerprints'], dict):
        cleaned['partialFingerprints'] = {k: str(v) for k, v in result['partialFingerprints'].items() if v}
    
    # Fix baselineState
    if 'baselineState' in result:
        state = fix_baseline_state(result['baselineState'])
        if state:
            cleaned['baselineState'] = state
    
    # Skip occurrenceCount if 0 (must be >= 1)
    if 'occurrenceCount' in result and isinstance(result['occurrenceCount'], int) and result['occurrenceCount'] >= 1:
        cleaned['occurrenceCount'] = result['occurrenceCount']
    
    # GUID fields
    if 'guid' in result and result['guid']:
        cleaned['guid'] = str(result['guid'])
    if 'correlationGuid' in result and result['correlationGuid']:
        cleaned['correlationGuid'] = str(result['correlationGuid'])
    
    return cleaned if cleaned.get('ruleId') else None


def clean_rule(rule):
    """Clean a rule object."""
    if not isinstance(rule, dict):
        return None
    
    cleaned = {}
    
    # Required: id
    if 'id' in rule:
        cleaned['id'] = str(rule['id'])
    else:
        return None
    
    # Optional string fields
    for field in ['name', 'helpUri']:
        if field in rule and rule[field]:
            cleaned[field] = str(rule[field])
    
    # Message fields
    for field in ['shortDescription', 'fullDescription', 'help']:
        if field in rule and isinstance(rule[field], dict):
            msg = rule[field]
            cleaned_msg = {}
            if 'text' in msg and msg['text']:
                cleaned_msg['text'] = str(msg['text'])
            if 'markdown' in msg and msg['markdown']:
                cleaned_msg['markdown'] = str(msg['markdown'])
            if cleaned_msg:
                cleaned[field] = cleaned_msg
    
    # defaultConfiguration
    if 'defaultConfiguration' in rule and isinstance(rule['defaultConfiguration'], dict):
        config = rule['defaultConfiguration']
        cleaned_config = {}
        if 'enabled' in config:
            cleaned_config['enabled'] = bool(config['enabled'])
        if 'level' in config:
            cleaned_config['level'] = fix_level(config['level'])
        if 'rank' in config and isinstance(config['rank'], (int, float)) and config['rank'] >= 0:
            cleaned_config['rank'] = float(config['rank'])
        if cleaned_config:
            cleaned['defaultConfiguration'] = cleaned_config
    
    return cleaned


def clean_sarif(sarif):
    """Clean the entire SARIF document."""
    cleaned = {
        '$schema': 'https://raw.githubusercontent.com/oasis-tcs/sarif-spec/master/Schemata/sarif-schema-2.1.0.json',
        'version': '2.1.0',
    }
    
    # Clean runs
    if 'runs' in sarif and isinstance(sarif['runs'], list):
        cleaned_runs = []
        for run in sarif['runs']:
            if not isinstance(run, dict):
                continue
            
            cleaned_run = {}
            
            # Clean tool
            if 'tool' in run and isinstance(run['tool'], dict):
                tool = run['tool']
                cleaned_tool = {}
                
                if 'driver' in tool and isinstance(tool['driver'], dict):
                    driver = tool['driver']
                    cleaned_driver = {}
                    
                    # Required: name
                    if 'name' in driver:
                        cleaned_driver['name'] = str(driver['name'])
                    
                    # Optional string fields
                    for field in ['organization', 'product', 'version', 'semanticVersion', 
                                  'fullName', 'downloadUri', 'informationUri']:
                        if field in driver and driver[field]:
                            cleaned_driver[field] = str(driver[field])
                    
                    # Message fields
                    for field in ['shortDescription', 'fullDescription']:
                        if field in driver and isinstance(driver[field], dict):
                            msg = driver[field]
                            cleaned_msg = {}
                            if 'text' in msg and msg['text']:
                                cleaned_msg['text'] = str(msg['text'])
                            if cleaned_msg:
                                cleaned_driver[field] = cleaned_msg
                    
                    # Clean rules
                    if 'rules' in driver and isinstance(driver['rules'], list):
                        cleaned_rules = []
                        for rule in driver['rules']:
                            cleaned_rule = clean_rule(rule)
                            if cleaned_rule:
                                cleaned_rules.append(cleaned_rule)
                        if cleaned_rules:
                            cleaned_driver['rules'] = cleaned_rules
                    
                    cleaned_tool['driver'] = cleaned_driver
                
                cleaned_run['tool'] = cleaned_tool
            
            # Clean results
            if 'results' in run and isinstance(run['results'], list):
                cleaned_results = []
                for result in run['results']:
                    cleaned_result = clean_result(result)
                    if cleaned_result:
                        cleaned_results.append(cleaned_result)
                cleaned_run['results'] = cleaned_results
            
            # Clean automationDetails
            if 'automationDetails' in run and isinstance(run['automationDetails'], dict):
                auto = run['automationDetails']
                cleaned_auto = {}
                if 'id' in auto and auto['id']:
                    cleaned_auto['id'] = str(auto['id'])
                if 'guid' in auto and auto['guid']:
                    cleaned_auto['guid'] = str(auto['guid'])
                if 'description' in auto and isinstance(auto['description'], dict):
                    desc = auto['description']
                    if 'text' in desc and desc['text']:
                        cleaned_auto['description'] = {'text': str(desc['text'])}
                if cleaned_auto:
                    cleaned_run['automationDetails'] = cleaned_auto
            
            # Optional run fields
            if 'columnKind' in run:
                kind = run['columnKind']
                if isinstance(kind, int):
                    cleaned_run['columnKind'] = 'utf16CodeUnits' if kind == 1 else 'unicodeCodePoints'
                elif isinstance(kind, str) and kind in ['utf16CodeUnits', 'unicodeCodePoints']:
                    cleaned_run['columnKind'] = kind
            
            if 'defaultEncoding' in run and run['defaultEncoding']:
                cleaned_run['defaultEncoding'] = 'UTF-8'
            
            cleaned_runs.append(cleaned_run)
        
        cleaned['runs'] = cleaned_runs
    
    return cleaned


def main():
    if len(sys.argv) < 2:
        print("Usage: python Clean-SarifForGitHub.py input.sarif [output.sarif]")
        sys.exit(1)
    
    input_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2]) if len(sys.argv) > 2 else input_path
    
    if not input_path.exists():
        print(f"Error: Input file not found: {input_path}")
        sys.exit(1)
    
    print(f"Reading: {input_path}")
    with open(input_path, 'r', encoding='utf-8') as f:
        sarif = json.load(f)
    
    print("Cleaning SARIF for GitHub compatibility...")
    cleaned = clean_sarif(sarif)
    
    # Count results
    result_count = sum(len(run.get('results', [])) for run in cleaned.get('runs', []))
    rule_count = sum(len(run.get('tool', {}).get('driver', {}).get('rules', [])) 
                     for run in cleaned.get('runs', []))
    
    print(f"Writing: {output_path}")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(cleaned, f, indent=2)
    
    print(f"✅ Done! {result_count} results, {rule_count} rules")
    print(f"   Version: {cleaned['version']}")
    

if __name__ == '__main__':
    main()
