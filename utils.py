import re
import ast
import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

_BOILERPLATE = re.compile(r"^make and share this .+ recipe from food\.com\.?$", re.IGNORECASE)

_supabase = None

def get_supabase_client():
    global _supabase
    if _supabase is None:
        _supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
    return _supabase


def parse_float(val):
    if val is None:
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def parse_list(val, field_name=""):
    """Parse R-style or Python list strings into a Python list. Pass-through if already a list."""
    if isinstance(val, list):
        return val
    if not val or val.strip() in ("NA", "NULL", "None", ""):
        return []
    try:
        result = ast.literal_eval(val)
        if isinstance(result, list):
            return result
        if isinstance(result, str):
            return [result]
        return []
    except Exception:
        pass
    match = re.match(r'^c\((.*)\)$', val.strip(), re.DOTALL)
    if match:
        inner = re.sub(r'\bNA\b', 'None', match.group(1))
        try:
            result = ast.literal_eval(f"[{inner}]")
            return [x for x in result if x is not None]
        except Exception as e:
            print(f"parse_list failed for {field_name}: {e}")
    return []


def clean_description(val):
    if not val:
        return None
    val = val.strip()
    return None if _BOILERPLATE.match(val) else val


def is_real_description(desc):
    desc = (desc or "").strip()
    return bool(desc) and not _BOILERPLATE.match(desc)
