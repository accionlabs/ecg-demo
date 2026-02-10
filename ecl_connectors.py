#!/usr/bin/env python3
"""
ECL Connectors Module - Enterprise System of Record Adapters
Provides abstract connector interfaces for enterprise data sources.

This module makes ECL extensible to ANY System of Record:
  - SharePoint (documents, contracts)
  - Dynamics 365 (CRM, accounts)
  - ServiceNow (ITSM tickets, assets)
  - Snowflake / Databricks (data warehouse)
  - AppXtender (legacy documents)
  - Custom REST APIs

Each connector implements a standard interface for:
  1. connect() — authenticate and establish connection
  2. list_documents() — enumerate available documents
  3. fetch_document() — retrieve document text for extraction
  4. push_results() — (optional) write extraction results back
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime
import json


# ============================================================
# SECTION 1: CONNECTOR BASE CLASS
# ============================================================

@dataclass
class DocumentMetadata:
    """Metadata for a document in a System of Record."""
    doc_id: str
    title: str
    source_system: str
    doc_type: str = ""
    created_at: str = ""
    modified_at: str = ""
    author: str = ""
    url: str = ""
    size_bytes: int = 0
    tags: List[str] = field(default_factory=list)


class BaseConnector:
    """
    Abstract base class for all ECL data source connectors.
    Every SoR connector must implement this interface.
    """

    def __init__(self, name: str, system_type: str):
        self.name = name
        self.system_type = system_type
        self.connected = False
        self.connection_timestamp: Optional[str] = None

    def connect(self, **credentials) -> bool:
        """Authenticate and establish connection. Returns True if successful."""
        raise NotImplementedError(f"{self.name} connector connect() not implemented")

    def disconnect(self):
        """Close connection and clean up."""
        self.connected = False

    def list_documents(self, filters: Dict = None) -> List[DocumentMetadata]:
        """List available documents, optionally filtered."""
        raise NotImplementedError(f"{self.name} connector list_documents() not implemented")

    def fetch_document(self, doc_id: str) -> str:
        """Fetch document text content by ID."""
        raise NotImplementedError(f"{self.name} connector fetch_document() not implemented")

    def push_results(self, doc_id: str, results: Dict) -> bool:
        """(Optional) Push extraction results back to the SoR."""
        return False  # Default: no writeback

    def health_check(self) -> Dict:
        """Check connector health and return status."""
        return {
            "connector": self.name,
            "system_type": self.system_type,
            "connected": self.connected,
            "timestamp": datetime.now().isoformat(),
        }


# ============================================================
# SECTION 2: SHAREPOINT CONNECTOR
# ============================================================

class SharePointConnector(BaseConnector):
    """
    Connector for Microsoft SharePoint document libraries.
    Supports: site_url, client_id, client_secret, tenant_id auth.
    """

    def __init__(self):
        super().__init__("SharePoint", "document_management")
        self.site_url: str = ""
        self.access_token: Optional[str] = None

    def connect(self, site_url: str = "", tenant_id: str = "",
                client_id: str = "", client_secret: str = "", **kwargs) -> bool:
        """
        Connect to SharePoint using app-only or delegated auth.
        In production, this would use msal + requests to obtain an OAuth2 token.
        """
        self.site_url = site_url
        # NOTE: Production implementation would call:
        # POST https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token
        # with client_credentials grant type
        print(f"  [SharePoint] Connecting to {site_url}...")
        print(f"  [SharePoint] Tenant: {tenant_id}")
        # Stub: mark as connected for now
        self.connected = True
        self.connection_timestamp = datetime.now().isoformat()
        print(f"  [SharePoint] ✓ Connected at {self.connection_timestamp}")
        return True

    def list_documents(self, filters: Dict = None) -> List[DocumentMetadata]:
        """
        List documents from a SharePoint document library.
        Production: GET https://{site}/sites/{site_id}/_api/web/lists/getbytitle('Documents')/items
        """
        if not self.connected:
            raise ConnectionError("SharePoint not connected. Call connect() first.")

        # Stub: return empty list (real impl would query SharePoint REST API)
        print(f"  [SharePoint] Listing documents (filters={filters})...")
        return []

    def fetch_document(self, doc_id: str) -> str:
        """
        Fetch document content from SharePoint.
        Production: Download file via SharePoint REST API + extract text.
        """
        if not self.connected:
            raise ConnectionError("SharePoint not connected.")
        print(f"  [SharePoint] Fetching document: {doc_id}")
        return ""


# ============================================================
# SECTION 3: DYNAMICS 365 CONNECTOR
# ============================================================

class Dynamics365Connector(BaseConnector):
    """
    Connector for Microsoft Dynamics 365 (CRM / ERP).
    Extracts accounts, contacts, opportunities, contracts.
    """

    def __init__(self):
        super().__init__("Dynamics365", "crm")
        self.org_url: str = ""

    def connect(self, org_url: str = "", client_id: str = "",
                client_secret: str = "", **kwargs) -> bool:
        """
        Connect to Dynamics 365 Web API.
        Production: OAuth2 token via Azure AD.
        """
        self.org_url = org_url
        print(f"  [Dynamics365] Connecting to {org_url}...")
        self.connected = True
        self.connection_timestamp = datetime.now().isoformat()
        print(f"  [Dynamics365] ✓ Connected at {self.connection_timestamp}")
        return True

    def list_documents(self, filters: Dict = None) -> List[DocumentMetadata]:
        """
        List entities from Dynamics 365.
        Production: GET {org_url}/api/data/v9.2/accounts?$select=name,accountnumber
        """
        if not self.connected:
            raise ConnectionError("Dynamics365 not connected.")
        print(f"  [Dynamics365] Listing records (filters={filters})...")
        return []

    def fetch_document(self, doc_id: str) -> str:
        """Fetch record/entity from Dynamics 365 as formatted text."""
        if not self.connected:
            raise ConnectionError("Dynamics365 not connected.")
        return ""


# ============================================================
# SECTION 4: SERVICENOW CONNECTOR
# ============================================================

class ServiceNowConnector(BaseConnector):
    """
    Connector for ServiceNow ITSM.
    Extracts incidents, change requests, assets, CMDB items.
    """

    def __init__(self):
        super().__init__("ServiceNow", "itsm")
        self.instance_url: str = ""

    def connect(self, instance_url: str = "", username: str = "",
                password: str = "", **kwargs) -> bool:
        """
        Connect to ServiceNow REST API.
        Production: Basic auth or OAuth2 with instance URL.
        """
        self.instance_url = instance_url
        print(f"  [ServiceNow] Connecting to {instance_url}...")
        self.connected = True
        self.connection_timestamp = datetime.now().isoformat()
        print(f"  [ServiceNow] ✓ Connected at {self.connection_timestamp}")
        return True

    def list_documents(self, filters: Dict = None) -> List[DocumentMetadata]:
        """Production: GET /api/now/table/{table}?sysparm_query=..."""
        if not self.connected:
            raise ConnectionError("ServiceNow not connected.")
        return []

    def fetch_document(self, doc_id: str) -> str:
        """Fetch record from ServiceNow as formatted text."""
        if not self.connected:
            raise ConnectionError("ServiceNow not connected.")
        return ""


# ============================================================
# SECTION 5: FILE SYSTEM CONNECTOR (READY)
# ============================================================

class FileSystemConnector(BaseConnector):
    """
    Local file system connector — the connector ECL uses today.
    This is fully functional, not a stub.
    """

    def __init__(self):
        super().__init__("FileSystem", "local")
        self.base_path: str = ""

    def connect(self, base_path: str = ".", **kwargs) -> bool:
        """Connect to a local directory."""
        import os
        self.base_path = os.path.abspath(base_path)
        if os.path.isdir(self.base_path):
            self.connected = True
            self.connection_timestamp = datetime.now().isoformat()
            print(f"  [FileSystem] ✓ Connected to {self.base_path}")
            return True
        print(f"  [FileSystem] ✗ Directory not found: {self.base_path}")
        return False

    def list_documents(self, filters: Dict = None) -> List[DocumentMetadata]:
        """List text/markdown files in directory."""
        import os
        if not self.connected:
            raise ConnectionError("FileSystem not connected.")

        docs = []
        extensions = filters.get("extensions", [".md", ".txt", ".pdf"]) if filters else [".md", ".txt", ".pdf"]

        for root, dirs, files in os.walk(self.base_path):
            for fname in files:
                if any(fname.endswith(ext) for ext in extensions):
                    fpath = os.path.join(root, fname)
                    stat = os.stat(fpath)
                    docs.append(DocumentMetadata(
                        doc_id=fpath,
                        title=fname,
                        source_system="FileSystem",
                        doc_type=os.path.splitext(fname)[1],
                        size_bytes=stat.st_size,
                        modified_at=datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    ))
        return docs

    def fetch_document(self, doc_id: str) -> str:
        """Read file contents as text."""
        with open(doc_id, 'r', errors='replace') as f:
            return f.read()


# ============================================================
# SECTION 6: CONNECTOR REGISTRY
# ============================================================

class ConnectorRegistry:
    """
    Central registry for managing ECL data source connectors.
    Supports plugging in new connectors at runtime.
    """

    def __init__(self):
        self.connectors: Dict[str, BaseConnector] = {}
        # Register built-in connectors
        self.register("filesystem", FileSystemConnector())
        self.register("sharepoint", SharePointConnector())
        self.register("dynamics365", Dynamics365Connector())
        self.register("servicenow", ServiceNowConnector())

    def register(self, name: str, connector: BaseConnector):
        """Register a new connector."""
        self.connectors[name] = connector

    def get(self, name: str) -> Optional[BaseConnector]:
        """Get a connector by name."""
        return self.connectors.get(name)

    def list_connectors(self) -> List[Dict]:
        """List all registered connectors and their status."""
        return [c.health_check() for c in self.connectors.values()]

    def list_available(self) -> List[str]:
        """List connector names."""
        return list(self.connectors.keys())


# ============================================================
# SECTION 7: MAIN / SELF-TEST
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("  ECL Connector Registry")
    print("=" * 60)

    registry = ConnectorRegistry()
    print(f"\n  Registered connectors: {registry.list_available()}")

    # Test FileSystem connector (the only fully functional one)
    fs = registry.get("filesystem")
    fs.connect(base_path=".")
    docs = fs.list_documents()
    print(f"  FileSystem docs found: {len(docs)}")
    for d in docs[:5]:
        print(f"    - {d.title} ({d.size_bytes:,} bytes)")

    print("\n  All connector statuses:")
    for status in registry.list_connectors():
        icon = "✓" if status["connected"] else "○"
        print(f"    [{icon}] {status['connector']} ({status['system_type']})")

    print("\n" + "=" * 60)
