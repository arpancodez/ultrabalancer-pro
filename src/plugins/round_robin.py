"""Round Robin Load Balancing Algorithm Plugin.

This module implements a simple round-robin load balancing algorithm
that distributes requests evenly across available servers in a circular fashion.

Author: UltraBalancer Pro
Version: 1.0.0
Auto-loaded by the plugin system.
"""


class RoundRobinAlgorithm:
    """Round Robin Load Balancing Algorithm.
    
    This algorithm distributes incoming requests to servers in a sequential,
    circular order. Each server receives requests in turn, ensuring an even
    distribution of load across all available servers.
    
    Attributes:
        name (str): The name identifier for this algorithm.
        current_index (int): Tracks the current position in the server list.
    """
    
    def __init__(self):
        """Initialize the Round Robin algorithm.
        
        Sets up the algorithm name and initializes the current index
        to start at the first server (index 0).
        """
        self.name = "round_robin"
        self.current_index = 0
    
    def select_server(self, servers):
        """Select the next server using round-robin strategy.
        
        Args:
            servers (list): List of available server instances.
            
        Returns:
            object: The selected server instance, or None if no servers available.
            
        Raises:
            None: This method handles empty server lists gracefully.
        """
        # Handle edge case: no servers available
        if not servers or len(servers) == 0:
            return None
        
        # Select the server at the current index
        selected_server = servers[self.current_index]
        
        # Move to the next server for the next request
        # Use modulo to wrap around to the beginning when reaching the end
        self.current_index = (self.current_index + 1) % len(servers)
        
        return selected_server
    
    def reset(self):
        """Reset the algorithm to its initial state.
        
        This method resets the current index back to 0, which can be useful
        when the server list changes or when restarting the load balancer.
        """
        self.current_index = 0
    
    def get_info(self):
        """Get information about this algorithm.
        
        Returns:
            dict: Dictionary containing algorithm metadata including:
                - name: Algorithm identifier
                - description: Brief description of the algorithm
                - current_index: Current position in the server rotation
        """
        return {
            "name": self.name,
            "description": "Distributes requests evenly across servers in circular order",
            "current_index": self.current_index
        }


# Plugin metadata for auto-loading
# The plugin loader will automatically detect and load this class
__plugin_class__ = RoundRobinAlgorithm
__plugin_name__ = "round_robin"
__plugin_version__ = "1.0.0"
__plugin_description__ = "Simple round-robin load balancing algorithm"
