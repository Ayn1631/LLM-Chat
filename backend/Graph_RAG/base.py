from langchain_neo4j import Neo4jGraph
import os
import dotenv
dotenv.load_dotenv()

graph = Neo4jGraph(refresh_schema=False)