from backend.database.supabase_client import supabase

try:
    resultado = (
        supabase.table("rol")
        .select("*")
        .execute()
    )

    print("CONEXION EXITOSA")
    print("Roles encontrados:", resultado.data)

except Exception as error:
    print("ERROR DE CONEXION:")
    print(error)
