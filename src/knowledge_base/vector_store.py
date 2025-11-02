"""Vector database for knowledge base."""
import os
from typing import List, Dict, Any
from pathlib import Path
import logging

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import TextLoader, CSVLoader
from langchain_community.vectorstores import Chroma, FAISS
from langchain_openai import OpenAIEmbeddings
from langchain_core.documents import Document

logger = logging.getLogger(__name__)


class KnowledgeBase:
    """Knowledge base with vector store."""
    
    def __init__(
        self,
        vector_db_type: str = "chroma",
        persist_directory: str = "./data/vectordb",
        embedding_model: str = "text-embedding-3-small",
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        collection_name: str = "email_agent_kb"
    ):
        """Initialize knowledge base.
        
        Args:
            vector_db_type: Type of vector DB ('chroma' or 'faiss')
            persist_directory: Directory to persist vector DB
            embedding_model: OpenAI embedding model name
            chunk_size: Size of text chunks
            chunk_overlap: Overlap between chunks
            collection_name: Name of the collection (for Chroma)
        """
        self.vector_db_type = vector_db_type.lower()
        self.persist_directory = persist_directory
        self.collection_name = collection_name
        self.embeddings = OpenAIEmbeddings(model=embedding_model)
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        )
        self.vectorstore = None
        
        # Create persist directory if it doesn't exist
        Path(persist_directory).mkdir(parents=True, exist_ok=True)
    
    def load_documents(self, documents_path: str) -> List[Document]:
        """Load documents from directory.
        
        Args:
            documents_path: Path to documents directory
            
        Returns:
            List of loaded documents
        """
        documents = []
        documents_path = Path(documents_path)
        
        if not documents_path.exists():
            logger.warning(f"Documents path does not exist: {documents_path}")
            return documents
        
        # Load different file types
        for file_path in documents_path.rglob("*"):
            if not file_path.is_file():
                continue
                
            try:
                if file_path.suffix in [".txt", ".md", ".markdown"]:
                    loader = TextLoader(str(file_path), encoding='utf-8')
                    docs = loader.load()
                    documents.extend(docs)
                    logger.info(f"Loaded {len(docs)} documents from {file_path}")
                elif file_path.suffix == ".csv":
                    loader = CSVLoader(str(file_path))
                    docs = loader.load()
                    documents.extend(docs)
                    logger.info(f"Loaded {len(docs)} documents from {file_path}")
                elif file_path.suffix == ".pdf":
                    # PDF support requires additional packages
                    try:
                        from langchain_community.document_loaders import PyPDFLoader
                        loader = PyPDFLoader(str(file_path))
                        docs = loader.load()
                        documents.extend(docs)
                        logger.info(f"Loaded {len(docs)} documents from {file_path}")
                    except ImportError:
                        logger.warning(f"PDF support not available. Install pypdf: pip install pypdf")
                        continue
                else:
                    logger.info(f"Skipping unsupported file type: {file_path}")
                    continue
                
            except Exception as e:
                logger.error(f"Error loading {file_path}: {e}")
        
        return documents
    
    def build_index(self, documents_path: str, reset: bool = True):
        """Build vector store index from documents.
        
        Args:
            documents_path: Path to documents directory
            reset: If True, delete existing collection before rebuilding
        """
        # Reset/delete old collection if requested
        if reset and self.vector_db_type == "chroma":
            try:
                logger.info(f"Resetting collection '{self.collection_name}'...")
                # Delete the old collection
                import chromadb
                client = chromadb.PersistentClient(path=self.persist_directory)
                try:
                    client.delete_collection(name=self.collection_name)
                    logger.info(f"Deleted old collection '{self.collection_name}'")
                except:
                    logger.info(f"No existing collection '{self.collection_name}' to delete")
            except Exception as e:
                logger.warning(f"Could not reset collection: {e}")
        
        # Load and split documents
        documents = self.load_documents(documents_path)
        
        if not documents:
            logger.error("No documents loaded! Cannot build empty knowledge base.")
            raise ValueError("No documents found to index")
        
        splits = self.text_splitter.split_documents(documents)
        logger.info(f"Split {len(documents)} documents into {len(splits)} chunks")
        
        # Create vector store with specific collection name
        if self.vector_db_type == "chroma":
            self.vectorstore = Chroma.from_documents(
                documents=splits,
                embedding=self.embeddings,
                persist_directory=self.persist_directory,
                collection_name=self.collection_name
            )
        elif self.vector_db_type == "faiss":
            self.vectorstore = FAISS.from_documents(
                documents=splits,
                embedding=self.embeddings
            )
            self.vectorstore.save_local(self.persist_directory)
        else:
            raise ValueError(f"Unsupported vector DB type: {self.vector_db_type}")
        
        logger.info(f"Vector store built successfully with {len(splits)} chunks")
    
    def load_index(self):
        """Load existing vector store index."""
        try:
            if self.vector_db_type == "chroma":
                self.vectorstore = Chroma(
                    persist_directory=self.persist_directory,
                    embedding_function=self.embeddings,
                    collection_name=self.collection_name
                )
                logger.info(f"Vector store loaded successfully (collection: {self.collection_name})")
            elif self.vector_db_type == "faiss":
                self.vectorstore = FAISS.load_local(
                    self.persist_directory,
                    self.embeddings,
                    allow_dangerous_deserialization=True
                )
                logger.info("Vector store loaded successfully")
            else:
                raise ValueError(f"Unsupported vector DB type: {self.vector_db_type}")
            
        except Exception as e:
            logger.error(f"Failed to load vector store: {e}")
            logger.info("Creating new vector store")
            self.vectorstore = None
    
    def search(self, query: str, top_k: int = 3) -> List[Document]:
        """Search for relevant documents.
        
        Args:
            query: Search query
            top_k: Number of top results to return
            
        Returns:
            List of relevant documents
        """
        if self.vectorstore is None:
            logger.warning("Vector store not initialized")
            return []
        
        try:
            results = self.vectorstore.similarity_search(query, k=top_k)
            return results
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []
    
    def add_documents(self, documents: List[Document]):
        """Add new documents to the vector store.
        
        Args:
            documents: List of documents to add
        """
        if self.vectorstore is None:
            logger.error("Vector store not initialized")
            return
        
        splits = self.text_splitter.split_documents(documents)
        self.vectorstore.add_documents(splits)
        logger.info(f"Added {len(splits)} document chunks to vector store")
