from utils import get_supabase_client


def _fetch(user_id: str) -> list[str]:
    sb = get_supabase_client()
    rows = (
        sb.table("user_pantry")
        .select("ingredient_name")
        .eq("user_id", user_id)
        .order("ingredient_name")
        .execute()
    )
    return [r["ingredient_name"] for r in rows.data]


def get_pantry(user_id: str) -> list[str]:
    return _fetch(user_id)


def add_to_pantry(user_id: str, ingredient_name: str) -> list[str]:
    name = ingredient_name.strip().lower()
    sb = get_supabase_client()
    sb.table("user_pantry").insert(
        {"user_id": user_id, "ingredient_name": name}
    ).execute()
    return _fetch(user_id)


def remove_from_pantry(user_id: str, ingredient_name: str) -> list[str]:
    name = ingredient_name.strip().lower()
    sb = get_supabase_client()
    sb.table("user_pantry").delete().eq("user_id", user_id).eq("ingredient_name", name).execute()
    return _fetch(user_id)
