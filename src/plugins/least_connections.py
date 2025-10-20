"""Least Connections Load Balancing Algorithm Plugin

This module implements the Least Connections load balancing algorithm,
which routes incoming requests to the backend server with the fewest
active connections. This approach helps distribute load more evenly,
especially when request processing times vary significantly.

Author: UltraBalancer Pro
Version: 1.0.0
"""

import threading
from typing import List, Dict, Optional
from collections import defaultdict


class LeastConnectionsAlgorithm:
    """Least Connections Load Balancing Algorithm
    
    This class implements the least connections algorithm for load balancing.
    It tracks the number of active connections to each backend server and
    routes new requests to the server with the fewest active connections.
    
    The algorithm is thread-safe and maintains connection counts across
    multiple concurrent requests.
    
    Attributes:
        servers (List[str]): List of available backend server addresses
        connections (Dict[str, int]): Dictionary tracking active connections per server
        lock (threading.Lock): Thread lock for safe concurrent access
    """
    
    def __init__(self, servers: List[str]):
        """Initialize the Least Connections algorithm
        
        Args:
            servers (List[str]): List of backend server addresses (e.g., ['192.168.1.1:8080', '192.168.1.2:8080'])
        
        Raises:
            ValueError: If the servers list is empty or None
        """
        if not servers:
            raise ValueError("Servers list cannot be empty")
        
        self.servers = servers
        # Initialize connection count to 0 for all servers
        self.connections = defaultdict(int)
        # Thread lock to ensure thread-safe operations
        self.lock = threading.Lock()
    
    def get_next_server(self) -> Optional[str]:
        """Get the next server with the least active connections
        
        This method finds the backend server with the minimum number of
        active connections and returns its address. In case of ties,
        the first server with the minimum count is returned.
        
        Returns:
            Optional[str]: Address of the server with least connections,
                          or None if no servers are available
        
        Thread Safety:
            This method is thread-safe and can be called concurrently
            from multiple threads.
        """
        with self.lock:
            if not self.servers:
                return None
            
            # Find the server with minimum active connections
            min_connections = float('inf')
            selected_server = None
            
            for server in self.servers:
                current_connections = self.connections[server]
                if current_connections < min_connections:
                    min_connections = current_connections
                    selected_server = server
            
            # Increment the connection count for the selected server
            if selected_server:
                self.connections[selected_server] += 1
            
            return selected_server
    
    def release_connection(self, server: str) -> None:
        """Release a connection from the specified server
        
        This method should be called when a request to a backend server
        completes, to decrement the active connection count.
        
        Args:
            server (str): The server address to release the connection from
        
        Thread Safety:
            This method is thread-safe and can be called concurrently
            from multiple threads.
        
        Note:
            Connection count will not go below 0, even if release is
            called more times than get_next_server for a given server.
        """
        with self.lock:
            if server in self.connections and self.connections[server] > 0:
                self.connections[server] -= 1
    
    def add_server(self, server: str) -> None:
        """Add a new server to the pool
        
        Dynamically adds a new backend server to the load balancing pool.
        The new server starts with 0 active connections.
        
        Args:
            server (str): The server address to add
        
        Thread Safety:
            This method is thread-safe and can be called concurrently
            from multiple threads.
        """
        with self.lock:
            if server not in self.servers:
                self.servers.append(server)
                self.connections[server] = 0
    
    def remove_server(self, server: str) -> bool:
        """Remove a server from the pool
        
        Removes a backend server from the load balancing pool.
        The server's connection count is also removed.
        
        Args:
            server (str): The server address to remove
        
        Returns:
            bool: True if the server was removed, False if it wasn't found
        
        Thread Safety:
            This method is thread-safe and can be called concurrently
            from multiple threads.
        """
        with self.lock:
            if server in self.servers:
                self.servers.remove(server)
                if server in self.connections:
                    del self.connections[server]
                return True
            return False
    
    def get_server_stats(self) -> Dict[str, int]:
        """Get current connection statistics for all servers
        
        Returns a snapshot of active connections for each server in the pool.
        Useful for monitoring and debugging purposes.
        
        Returns:
            Dict[str, int]: Dictionary mapping server addresses to their
                           active connection counts
        
        Thread Safety:
            This method is thread-safe and returns a copy of the current state.
        """
        with self.lock:
            # Return a copy to prevent external modification
            return dict(self.connections)
    
    def reset_connections(self) -> None:
        """Reset all connection counts to zero
        
        This method resets the connection counter for all servers.
        Useful for testing or recovery scenarios.
        
        Thread Safety:
            This method is thread-safe and can be called concurrently
            from multiple threads.
        
        Warning:
            Use with caution in production environments as it may cause
            temporary imbalance if active connections are still ongoing.
        """
        with self.lock:
            for server in self.servers:
                self.connections[server] = 0
    
    def __repr__(self) -> str:
        """String representation of the algorithm instance
        
        Returns:
            str: A string describing the algorithm and its current state
        """
        return f"LeastConnectionsAlgorithm(servers={len(self.servers)}, total_connections={sum(self.connections.values())})"
