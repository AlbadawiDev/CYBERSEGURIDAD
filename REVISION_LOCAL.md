# Verificación offline

```powershell
python -X utf8 -m unittest discover -v
```

Estas pruebas usan archivos JSON temporales y un cliente vectorial simulado. No escanean redes, buscan personas, prueban contraseñas ni descargan modelos. Se comprobó conservación del historial corrupto y escritura atómica; no se ha probado escritura concurrente entre procesos.

`knowledge_db.py` resuelve `docs` y `chroma_db` junto al script. Permite `KNOWLEDGE_DB_PATH` y `KNOWLEDGE_DOCS_PATH`. Importar el módulo no crea una base ni requiere ChromaDB. ChromaDB es opcional para ese comando y debe instalarse y fijarse en un entorno separado después de validar sus embeddings y permisos de los documentos.

Se declaró la dependencia faltante [googlesearch-python](https://pypi.org/project/googlesearch-python/), que proporciona `from googlesearch import search`. No se ejecutó scraping ni WHOIS. El módulo de fuerza bruta web continúa como plantilla con TODOs; no representa una funcionalidad terminada.

Antes de usar documentación en el portafolio, revisar datos académicos y permisos de los PDF/libros incluidos. Esta revisión no publica, elimina ni transforma esos documentos. Faltan lock reproducible, mocks de DNS/SMB y pruebas de contratos de los ocho módulos.


## Contratos y arranque comprobados

Con `requirements.txt` instalado en una `.venv`, se verificaron además:

```powershell
python -X utf8 -m unittest discover -s tests-contracts -v
python -X utf8 auditoria.py --help
```

La suite de contratos usa mocks de DNS, WHOIS, Google, ping, sockets y FTP. No establece conexiones con objetivos ni registra credenciales reales. El schema prometido por README faltaba: se agregó `docs/schema_resultados.json`; los fallos del orquestador incluyen grupo0/timestamp y los resultados inválidos se rechazan. SMB dejó de afirmar éxito en una plantilla y se corrigió su SyntaxError; web continúa pendiente y declara NotImplementedError. Entradas inválidas de puertos producen error antes de crear sockets, los duplicados se consultan una vez y los sockets se liberan aun al fallar.

No se implementaron ataques nuevos ni se ejecutó fuerza bruta real. Estas pruebas demuestran los contratos con dobles de prueba, no la exactitud de respuestas de servidores remotos.
