import subprocess
import os
import shutil
import tempfile

repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
frontend_dir = os.path.join(repo_root, "frontend")
dist_dir = os.path.join(frontend_dir, "dist")

print("Building frontend...")
subprocess.run(["npm", "run", "build"], cwd=frontend_dir, check=True, shell=True)

temp_dir = tempfile.mkdtemp()

try:
    print(f"Copying built assets to temp dir: {temp_dir}...")
    for item in os.listdir(dist_dir):
        s = os.path.join(dist_dir, item)
        d = os.path.join(temp_dir, item)
        if os.path.isdir(s):
            shutil.copytree(s, d)
        else:
            shutil.copy2(s, d)

    # Add .nojekyll so GitHub Pages doesn't ignore assets with underscores
    with open(os.path.join(temp_dir, ".nojekyll"), "w") as f:
        pass

    # Initialize a clean git repo in temp_dir
    print("Pushing to gh-pages branch...")
    subprocess.run(["git", "init"], cwd=temp_dir, check=True)
    subprocess.run(["git", "checkout", "-b", "gh-pages"], cwd=temp_dir, check=True)
    subprocess.run(["git", "add", "."], cwd=temp_dir, check=True)
    subprocess.run(["git", "commit", "-m", "Deploy CedarShield Dashboard to GitHub Pages"], cwd=temp_dir, check=True)
    
    # Get origin URL
    origin_url = subprocess.check_output(["git", "config", "--get", "remote.origin.url"], text=True).strip()
    subprocess.run(["git", "remote", "add", "origin", origin_url], cwd=temp_dir, check=True)
    subprocess.run(["git", "push", "-f", "origin", "gh-pages"], cwd=temp_dir, check=True)
    print("\nSUCCESS! Deployed to branch 'gh-pages'!")
finally:
    shutil.rmtree(temp_dir, ignore_errors=True)
