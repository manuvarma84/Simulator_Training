import zipfile
import os

zipf = zipfile.ZipFile("C:/Users/hp/Desktop/python/change_sim_web/business_sim_v1.0.2.zip", "w", zipfile.ZIP_DEFLATED)

for root, dirs, files in os.walk("."):
    if "__pycache__" in root:
        continue
    for file in files:
        if file.endswith(".pyc"):
            continue
        filepath = os.path.join(root, file)
        zipf.write(filepath, os.path.relpath(filepath, "."))

zipf.close()
