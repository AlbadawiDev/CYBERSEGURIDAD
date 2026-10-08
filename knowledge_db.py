import os
import re
import argparse
import sys
from pathlib import Path

# Importar el módulo no crea bases de datos ni descarga modelos.
BASE_DIR = Path(__file__).resolve().parent
DB_PATH = Path(os.environ.get("KNOWLEDGE_DB_PATH", str(BASE_DIR / "chroma_db")))
DOCS_PATH = Path(os.environ.get("KNOWLEDGE_DOCS_PATH", str(BASE_DIR / "docs")))
client = None


def get_client():
    global client
    if client is None:
        try:
            import chromadb
        except ImportError as exc:
            raise RuntimeError("Instale la dependencia opcional: pip install chromadb") from exc
        client = chromadb.PersistentClient(path=str(DB_PATH))
    return client


def markdown_records(topic, content):
    """Extrae sólo secciones ## con contenido, incluso al inicio del archivo."""
    sections = re.split(r"^## +", content, flags=re.MULTILINE)[1:]
    records = []
    for section in sections:
        title, _, body = section.partition("\n")
        if title.strip() and body.strip():
            records.append((title.strip(), body.strip()))
    return records

def get_collection(topic: str):
    """Obtiene o crea una colección basada en el nombre del tema."""
    if not re.fullmatch(r"[A-Za-z0-9_-]+", topic):
        raise ValueError("El tema sólo permite letras, números, guion y guion bajo.")
    return get_client().get_or_create_collection(name=f"{topic}_errors")

def process_markdown_and_populate(topic: str):
    """Lee un archivo .md, extrae errores y soluciones, y los inserta en su colección."""
    if not re.fullmatch(r"[A-Za-z0-9_-]+", topic):
        raise ValueError("Tema inválido.")
    file_path = DOCS_PATH / f"{topic}.md"
    if not os.path.exists(file_path):
        print(f"Archivo no encontrado: {file_path}")
        return

    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    documents = []
    metadatas = []
    ids = []

    for i, (title, body) in enumerate(markdown_records(topic, content)):
        
        # Preparamos los registros
        documents.append(body)
        metadatas.append({"title": title})
        ids.append(f"{topic}_error_{i+1}")

    # Insertar en ChromaDB (upsert inserta o actualiza si el ID ya existe)
    if documents:
        collection = get_collection(topic)
        collection.upsert(
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )
        print(f"✅ Se indexaron {len(documents)} registros de errores de '{topic}' en ChromaDB.\n")

def query_error(topic: str, query_text: str, n_results: int = 2, threshold: float = 1.2):
    """Realiza una búsqueda semántica en la base de datos de errores."""
    if n_results <= 0:
        raise ValueError("n_results debe ser positivo.")
    collection = get_collection(topic)
    count = collection.count()
    if count == 0:
        print(f"⚠️ La colección '{topic}' está vacía o el archivo .md no existe.")
        return
        
    results = collection.query(
        query_texts=[query_text],
        n_results=min(n_results, count)
    )
    
    print(f"🔍 Resultados para la búsqueda en '{topic}': '{query_text}'\n" + "="*60)
    encontrados = 0
    for i in range(len(results['ids'][0])):
        title = results['metadatas'][0][i]['title']
        document = results['documents'][0][i]
        distance = results['distances'][0][i] if 'distances' in results and results['distances'] else "N/A"
        
        # Ignoramos los resultados que superen la distancia permitida
        if isinstance(distance, float) and distance > threshold:
            continue
            
        encontrados += 1
        dist_str = f"{distance:.4f}" if isinstance(distance, float) else str(distance)
        print(f"📌 Título: {title} (Distancia: {dist_str})")
        print(f"📄 Contenido:\n{document}\n" + "-"*60)
        
    if encontrados == 0:
        print(f"⚠️ No se encontraron resultados relevantes (umbral de distancia > {threshold}).")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Base de datos vectorial de errores y conocimientos")
    parser.add_argument("-q", "--query", type=str, help="Búsqueda del error en lenguaje natural")
    parser.add_argument("-u", "--update", action="store_true", help="Actualiza la base de datos leyendo el archivo .md correspondiente")
    parser.add_argument("-c", "--collection", type=str, default="latex", help="Tema a consultar/actualizar (por defecto: latex). Busca docs/<tema>.md")
    parser.add_argument("-t", "--threshold", type=float, default=1.2, help="Umbral de distancia máxima permitida (ej. 1.2)")
    
    args = parser.parse_args()
    collection = get_collection(args.collection)

    # 1. Extraemos de markdown y poblamos la BD Vectorial solo si se pide o si está vacía
    if args.update or collection.count() == 0:
        process_markdown_and_populate(args.collection)
    
    # 2. Hacemos la consulta si se proporcionó una
    if args.query:
        query_error(args.collection, args.query, threshold=args.threshold)
    elif not args.update:
        script_name = os.path.basename(sys.argv[0])
        print(f"💡 Sugerencia: Puedes buscar errores usando: python {script_name} -c {args.collection} -q 'tu error'")
        consulta_ejemplo = "Me da error Missing $ cuando escribo texto con guiones bajos"
        query_error(args.collection, consulta_ejemplo, threshold=args.threshold)
