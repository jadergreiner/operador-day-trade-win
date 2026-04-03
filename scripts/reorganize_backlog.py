import os
import re

def parse_markdown(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        
    intro_lines = []
    
    # We will just parse the document into sections
    # A block starting with "## " is a level 2 section
    # A block starting with "### " is a level 3 section
    # A block starting with "#### " is a level 4 task
    
    sections = []
    current_section = None
    current_subsection = None
    current_task = None
    
    result = {"intro": [], "main_sections": []}
    
    idx = 0
    state = "intro"
    
    while idx < len(lines):
        line = lines[idx]
        
        if line.startswith("## ") and state != "task_content" and "Fora do backlog ativo" not in line and "Estado atual" not in line:
            state = "main_section"
            current_section = {"header": line, "subsections": [], "content": []}
            result["main_sections"].append(current_section)
            current_subsection = None
            current_task = None
        elif line.startswith("### ") and state in ["main_section", "subsection_content", "task_content"] and current_section:
            state = "subsection"
            current_subsection = {"header": line, "tasks": [], "content": []}
            current_section["subsections"].append(current_subsection)
            current_task = None
        elif line.startswith("#### ") and state in ["main_section", "subsection", "task_content", "subsection_content"] and current_subsection:
            state = "task"
            current_task = {"header": line, "content": [], "status": "PENDENTE"}
            current_subsection["tasks"].append(current_task)
        else:
            if state == "intro":
                result["intro"].append(line)
            if state == "task":
                state = "task_content"
                current_task["content"].append(line)
                if "**Status:**" in line or "**Status**:" in line or "Status:" in line:
                    if "DONE" in line.upper() or "CONCLUIDO" in line.upper() or "✅" in line:
                        current_task["status"] = "DONE"
            elif state == "task_content":
                current_task["content"].append(line)
                if "**Status:**" in line or "**Status**:" in line or "Status:" in line:
                    if "DONE" in line.upper() or "CONCLUIDO" in line.upper() or "✅" in line:
                        current_task["status"] = "DONE"
            elif state == "subsection":
                state = "subsection_content"
                current_subsection["content"].append(line)
            elif state == "subsection_content":
                current_subsection["content"].append(line)
            elif state == "main_section":
                current_section["content"].append(line)
            elif state == "intro":
                pass # Handled above
            else:
                pass
                
        idx += 1
        
    return result
    
def write_markdown(parsed, filepath):
    with open(filepath, 'w', encoding='utf-8') as f:
        # Write intro
        f.writelines(parsed["intro"])
        
        completed_tasks = []
        
        # Priority order
        priority_order = {"P0": 0, "P1": 1, "P2": 2, "BUG": 0, "INFRA": 1, "ML": 1, "TECH": 1}
        
        for ms in parsed["main_sections"]:
            f.write(ms["header"])
            f.writelines(ms["content"])
            
            # Subsections often indicate priority "### P0 - Bloqueadores", etc
            
            for sub in ms["subsections"]:
                # Only write out pending tasks here
                pending = [t for t in sub["tasks"] if t["status"] != "DONE"]
                done = [t for t in sub["tasks"] if t["status"] == "DONE"]
                
                # Append done to global
                for d in done:
                    # add context to header
                    d["header"] = d["header"].strip() + f" ({ms['header'].strip().replace('## ', '')})\n"
                    completed_tasks.append(d)
                    
                if pending or sub["content"]:
                    f.write(sub["header"])
                    f.writelines(sub["content"])
                    for pt in pending:
                        f.write(pt["header"])
                        f.writelines(pt["content"])
                        
        if completed_tasks:
            f.write("## Tarefas Concluídas\n\n")
            for d in completed_tasks:
                f.write(d["header"])
                f.writelines(d["content"])
                
if __name__ == "__main__":
    filepath = 'docs/BACKLOG.md'
    parsed = parse_markdown(filepath)
    # create a backup just in case
    import shutil
    shutil.copy(filepath, filepath + ".bak")
    write_markdown(parsed, filepath)
    print("BACKLOG.md reorganized successfully.")

