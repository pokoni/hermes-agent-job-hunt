import subprocess, sys, os

workspace = '/Users/huyaohua/PycharmProjects/hermes-agent-job-hunt/job-hunt'
basename = 'パーソナルAIエージェント向けLLMのためのプロンプト最適化技術の検討_7197f0b25e6f'
os.chdir(workspace)

docx_script = os.path.join(workspace, 'skills', 'resume-tailor', 'scripts', 'export_resume_artifacts.py')
r1 = subprocess.run([sys.executable, docx_script, '--workspace', workspace, '--basename', basename],
                    capture_output=True, text=True)
print('=== DOCX ===')
print(r1.stdout[:3000])
if r1.stderr:
    print('STDERR:', r1.stderr[:2000])
print('RC:', r1.returncode)

if r1.returncode == 0:
    pdf_script = os.path.join(workspace, 'skills', 'resume-tailor', 'scripts', 'export_resume_pdfs.py')
    r2 = subprocess.run([sys.executable, pdf_script, '--workspace', workspace, '--basename', basename],
                        capture_output=True, text=True)
    print('=== PDF ===')
    print(r2.stdout[:3000])
    if r2.stderr:
        print('STDERR:', r2.stderr[:2000])
    print('RC:', r2.returncode)

# List outcomes
print('\n=== Final outputs ===')
for f in os.listdir(os.path.join(workspace, 'outputs', 'resumes')):
    if '7197f0b25e6f' in f and (f.endswith('.md') or f.endswith('.docx') or f.endswith('.pdf') or f.endswith('.json')):
        fp = os.path.join(workspace, 'outputs', 'resumes', f)
        sz = os.path.getsize(fp)
        print(f'  {f} ({sz} bytes)')
