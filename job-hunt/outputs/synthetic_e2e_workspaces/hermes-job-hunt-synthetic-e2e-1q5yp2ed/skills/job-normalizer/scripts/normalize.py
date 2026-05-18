#!/usr/bin/env python3
"""
Normalize raw job markdown files into schema-compliant JSON.
Enhanced mapping with compensation, keywords, remote policy.
"""
import yaml
import json
import re
import sys
from pathlib import Path
from datetime import date

def parse_raw_md(path):
    content = Path(path).read_text(encoding='utf-8')
    # split front matter
    match = re.match(r'^---\n(.*?)\n---\n(.*)$', content, re.DOTALL)
    if not match:
        raise ValueError(f"No YAML front matter found in {path}")
    front = match.group(1)
    body = match.group(2)
    # parse YAML with date handling
    def date_constructor(loader, node):
        value = loader.construct_scalar(node)
        # return as string
        return value
    yaml.SafeLoader.add_constructor('tag:yaml.org,2002:timestamp', date_constructor)
    meta = yaml.safe_load(front)
    # parse sections
    sections = {}
    current = None
    lines = body.split('\n')
    for line in lines:
        if line.startswith('## '):
            current = line[3:].strip()
            sections[current] = []
        elif current and line.strip() and line.startswith('- '):
            sections[current].append(line[2:].strip())
    return meta, sections, content

def parse_compensation(text):
    # text like "想定年収: 400万円〜700万円"
    pattern = r'(\d+)\s*万円\s*[〜~\-]\s*(\d+)\s*万円'
    match = re.search(pattern, text)
    if match:
        min_val = int(match.group(1)) * 10000
        max_val = int(match.group(2)) * 10000
        return {'currency': 'JPY', 'min': min_val, 'max': max_val, 'bonus_notes': None}
    # single number
    pattern2 = r'(\d+)\s*万円'
    match2 = re.search(pattern2, text)
    if match2:
        val = int(match2.group(1)) * 10000
        return {'currency': 'JPY', 'min': val, 'max': val, 'bonus_notes': None}
    return None

def infer_remote_policy(location_str, employment_details):
    # employment_details list of strings
    combined = location_str + ' ' + ' '.join(employment_details)
    combined_lower = combined.lower()
    if 'リモートワーク可' in combined or 'remote' in combined_lower:
        if '週' in combined and '1' in combined:
            # hybrid with limited remote days
            return 'hybrid'
        else:
            return 'remote'
    if 'フレックス' in combined or 'flex' in combined_lower:
        return 'hybrid'
    if '出社' in combined or 'office' in combined_lower or '勤務地' in combined:
        return 'onsite'
    return 'unknown'

def map_to_schema(meta, sections, raw_content):
    """Map raw data to schema-compliant dict."""
    # source
    source = meta.get('source_platform', 'unknown')
    # url
    url = meta.get('source_url', '')
    # company_name
    company_name = meta.get('company_name', '')
    # job_title
    job_title = meta.get('job_title', '')
    # location
    location_str = meta.get('location', '')
    # parse location string
    country = 'Japan'
    city = ''
    # simple city extraction
    if 'Tokyo' in location_str:
        city = 'Tokyo'
    elif 'Fukuoka' in location_str:
        city = 'Fukuoka'
    else:
        city = location_str.split()[0] if location_str else ''
    # remote_policy
    employment_details = sections.get('Visible employment details', [])
    remote_policy = infer_remote_policy(location_str, employment_details)
    location = {
        'country': country,
        'city': city,
        'remote_policy': remote_policy
    }
    # employment_type
    employment_type = meta.get('employment_type', 'unknown')
    # language_requirement
    japanese_level = 'not_specified'
    english_level = 'not_specified'
    notes = ''
    # check required skills for language mentions
    required = sections.get('Visible requirements', [])
    for skill in required:
        if '日本語' in skill or 'Japanese' in skill:
            if 'JLPT N1' in skill:
                japanese_level = 'JLPT N1'
            elif 'ビジネスレベル' in skill:
                japanese_level = 'business'
            else:
                japanese_level = skill.strip()
        if '英語' in skill or 'English' in skill:
            english_level = 'business'
    # also check general eligibility section
    if 'General internship eligibility visible on official internship page' in sections:
        for line in sections['General internship eligibility visible on official internship page']:
            if '日本語または英語' in line:
                notes = 'Japanese or English communication ability required'
                if english_level == 'not_specified':
                    english_level = 'business'
    # Build descriptive values instead of fabricating "none"
    japanese_final = japanese_level if japanese_level != 'not_specified' else 'not_specified (check raw description for details)'
    english_final = english_level if english_level != 'not_specified' else 'not_specified (source does not mention English requirement)'
    language_requirement = {
        'japanese_level': japanese_final,
        'english_level': english_final,
        'notes': notes if notes else None
    }
    # required_skills
    required_skills = sections.get('Visible requirements', [])
    # preferred_skills
    preferred_skills = sections.get('Preferred / plus factors', [])
    # responsibilities
    responsibilities = sections.get('Visible responsibilities', [])
    if not responsibilities:
        responsibilities = sections.get('Source snapshot', [])
    if not responsibilities:
        responsibilities = ['See raw description']
    # application_method
    application_method = 'platform_apply'  # default
    # raw_description
    raw_description = raw_content
    # source_job_id
    source_job_id = meta.get('job_id')
    # company_profile
    company_profile = None
    # department
    department = None
    # must_have_years_experience
    must_have_years_experience = None
    # compensation
    compensation = None
    for line in employment_details:
        if '万円' in line:
            comp = parse_compensation(line)
            if comp:
                compensation = comp
                break
    # visa_support
    visa_support = None
    # application_deadline
    application_deadline = None
    # screening_process
    screening_process = None
    # keywords_normalized
    keywords_normalized = []
    if 'Visible stack / keywords' in sections:
        for item in sections['Visible stack / keywords']:
            # split by commas, slashes, etc.
            parts = re.split(r'[,、/]', item)
            for part in parts:
                part = part.strip()
                if part:
                    keywords_normalized.append(part)
    # fit_hints
    fit_hints = None
    # fetched_at
    fetched_at = meta.get('retrieved_at')
    if isinstance(fetched_at, date):
        fetched_at = fetched_at.isoformat()
    
    # Build output dict
    out = {
        'source': source,
        'url': url,
        'company_name': company_name,
        'job_title': job_title,
        'location': location,
        'employment_type': employment_type,
        'language_requirement': language_requirement,
        'required_skills': required_skills,
        'preferred_skills': preferred_skills,
        'responsibilities': responsibilities,
        'application_method': application_method,
        'raw_description': raw_description,
        'source_job_id': source_job_id,
        'company_profile': company_profile,
        'department': department,
        'must_have_years_experience': must_have_years_experience,
        'compensation': compensation,
        'visa_support': visa_support,
        'application_deadline': application_deadline,
        'screening_process': screening_process,
        'keywords_normalized': keywords_normalized,
        'fit_hints': fit_hints,
        'fetched_at': fetched_at
    }
    return out

def validate_against_schema(data, schema_path):
    import jsonschema
    with open(schema_path, 'r', encoding='utf-8') as f:
        schema = json.load(f)
    jsonschema.validate(instance=data, schema=schema)

def main():
    raw_dir = Path('data/raw_jobs')
    output_dir = Path('data/jobs')
    schema_path = Path('data/job_posting.schema.json')
    
    for raw_path in raw_dir.glob('*.md'):
        if raw_path.name == 'raw_job_format.md':
            continue
        print(f'Processing {raw_path.name}')
        meta, sections, raw_content = parse_raw_md(raw_path)
        data = map_to_schema(meta, sections, raw_content)
        # validate
        try:
            validate_against_schema(data, schema_path)
        except Exception as e:
            print(f'  Validation error: {e}')
            sys.exit(1)
        # write output
        out_path = output_dir / raw_path.with_suffix('.json').name
        with open(out_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f'  -> {out_path}')

if __name__ == '__main__':
    main()