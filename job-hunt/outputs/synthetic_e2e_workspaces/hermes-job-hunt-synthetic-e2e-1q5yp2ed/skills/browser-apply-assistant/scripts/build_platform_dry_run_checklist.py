#!/usr/bin/env python3
from __future__ import annotations
import argparse, json
from datetime import datetime, timezone
from pathlib import Path

def now(): return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00","Z")
def load(p:Path): return json.loads(p.read_text(encoding="utf-8"))
def find(profiles:dict,pid:str)->dict:
    for p in profiles.get("platforms",[]):
        if p.get("platform_id")==pid: return p
    raise KeyError(f"Unknown platform_id: {pid}")
def job_summary(path:Path)->dict:
    d=load(path)
    return {"job_basename":path.stem,"job_id":d.get("job_id") or d.get("id") or path.stem,
            "company_name":d.get("company_name") or d.get("company") or "",
            "job_title":d.get("job_title") or d.get("title") or "",
            "application_url":d.get("application_url") or d.get("url") or d.get("source_url") or ""}
def build(ws:Path,job:Path,profiles:Path,pid:str)->dict:
    prof=load(profiles); p=find(prof,pid); j=job_summary(job); prefix=f"{j['job_basename']}_{pid}_platform_dry_run"
    return {"job_basename":j["job_basename"],"job_id":j["job_id"],"company_name":j["company_name"],"job_title":j["job_title"],
            "application_url":j["application_url"],"platform_id":p["platform_id"],"platform_name":p["platform_name"],
            "access_mode":p["access_mode"],"automation_allowed":p["automation_allowed"],
            "manual_intervention_required":p["manual_intervention_required"],"login_strategy":p["login_strategy"],
            "form_discovery_strategy":p.get("form_discovery_strategy",""),"artifact_upload_strategy":p.get("artifact_upload_strategy",""),
            "allowed_actions":p["allowed_actions"],"forbidden_actions":p["forbidden_actions"],"stop_conditions":p["stop_conditions"],
            "submission_boundary":prof["submission_boundary"],"human_approval_required":True,
            "status":"blocked" if p["manual_intervention_required"] else "review_required","created_at":now(),
            "outputs":{"json":f"outputs/logs/{prefix}.json","markdown":f"outputs/logs/{prefix}.md"}}
def md(c:dict)->str:
    lines=["# Platform Browser Dry-Run Checklist","","## Target Job","",
           f"- Job basename: `{c['job_basename']}`",f"- Company: {c['company_name'] or 'Unknown'}",
           f"- Job title: {c['job_title'] or 'Unknown'}",f"- Application URL: {c['application_url'] or 'Unknown'}","",
           "## Platform Strategy","",f"- Platform: `{c['platform_id']}` / {c['platform_name']}",
           f"- Access mode: `{c['access_mode']}`",f"- Automation allowed: `{c['automation_allowed']}`",
           f"- Manual intervention required: `{c['manual_intervention_required']}`",f"- Login strategy: {c['login_strategy']}","",
           "## Form Discovery Strategy","",c["form_discovery_strategy"] or "- Not specified.","",
           "## Artifact Upload Strategy","",c["artifact_upload_strategy"] or "- Not specified.","",
           "## Allowed Actions",""]
    lines += [f"- {x}" for x in c["allowed_actions"]]
    lines += ["","## Forbidden Actions",""]+[f"- {x}" for x in c["forbidden_actions"]]
    lines += ["","## Stop Conditions",""]+[f"- {x}" for x in c["stop_conditions"]]
    lines += ["","## Human Approval Boundary","","Explicit approval is required."]+c["submission_boundary"]
    lines += ["","## Dry-Run Result","",f"- Status: `{c['status']}`","- No website was accessed by this checklist generator.",
              "- No credentials were stored.","- No files were uploaded.","- No submit button was clicked.",""]
    return "\n".join(lines)
def main()->int:
    ap=argparse.ArgumentParser()
    ap.add_argument("--workspace",default=".")
    ap.add_argument("--job",required=True)
    ap.add_argument("--profiles",default="data/platform_session_strategy_profiles.json")
    ap.add_argument("--platform-id",required=True)
    a=ap.parse_args()
    ws=Path(a.workspace).resolve()
    job=(ws/a.job).resolve() if not Path(a.job).is_absolute() else Path(a.job)
    profiles=(ws/a.profiles).resolve() if not Path(a.profiles).is_absolute() else Path(a.profiles)
    c=build(ws,job,profiles,a.platform_id)
    jp=ws/c["outputs"]["json"]; mp=ws/c["outputs"]["markdown"]; jp.parent.mkdir(parents=True,exist_ok=True)
    jp.write_text(json.dumps(c,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    mp.write_text(md(c),encoding="utf-8")
    print(json.dumps(c,ensure_ascii=False,indent=2))
    return 0
if __name__=="__main__": raise SystemExit(main())
