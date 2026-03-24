
import os
import re
from typing import Dict


class SaveDiagramTool:
    @staticmethod
    def save_diagram(content: str, file_name: str, file_type: str) -> Dict:
        try:
            directory =  "generated_diagrams"
            os.makedirs(directory, exist_ok = True)
            
            file_name = re.sub(r'[^a-zA-Z0-9_-]', '_', file_name)
            
            file_path = os.path.join(directory, f"{file_name}.{file_type}")
            
            if os.path.exists(file_path):
                version = 2
                while True:
                    versioned_name= f"{file_name}_v{version}"
                    versioned_path = os.path.join(directory, f"{versioned_name}.{file_type}")
                    
                    if not os.path.exists(versioned_path):
                        file_path = versioned_path
                        break
                
                    version +=1
                
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(content)

            return {
                "success": True,
                "file_path": file_path,
                "message": "Arquivo salvo"
            }
                
        except Exception as e:
            return {
                "success": False,
                "errors": [str(e)]
            }