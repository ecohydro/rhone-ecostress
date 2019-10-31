from pathlib import Path
import shutil

root_path = Path("/scratch/rave")

task_paths = list(root_path.glob("task*"))

for path in task_paths:
    print(str(list(path.glob("*"))[0]))

qa_path = Path(root_path, "rhone-ecostress-data", "ECO3ANCQA")
et_path = Path(root_path, "rhone-ecostress-data", "ECO3ETPTJPL")
esi_path = Path(root_path, "rhone-ecostress-data", "ECO4ESIPTJPL")

def sort_task_to_product_folders(task_folder_paths, product_folder_paths):
    """
    Takes downloaded task folders from appeears downlaod script and sorts into named product folders.
    The name of the product folder must be the unique name of the ECOSTRESS product (not the layer).
    Product = ECO3ETPTJPL Layer = ETinstUncertainty
    """
    for path in product_folder_paths:
        if path.exists() == False:
            path.mkdir(parents=True)
            
    product_names = [path.name for path in product_folder_paths]
    
    for path in task_folder_paths:
        files_iter = path.glob("*")
        for file in files_iter:
            for name in product_names:
                if name in str(file):
                    dest_path = [product_folder_path for product_folder_path in product_folder_paths if name in str(product_folder_path)][0]
                    shutil.copy(str(file), str(dest_path)) # this currently overwrites files with the same name, possibly csvs and xml
    
sort_task_to_product_folders(task_paths, [qa_path, et_path, esi_path])