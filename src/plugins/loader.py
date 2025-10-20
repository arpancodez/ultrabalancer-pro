import os
import importlib
import importlib.util
import sys
from pathlib import Path
from typing import Dict, Type, Optional
import logging
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

logger = logging.getLogger(__name__)

class PluginLoader:
    """Dynamic plugin loader with auto-discovery and hot-reload support."""
    
    def __init__(self, plugin_dir: str = "src/plugins/algorithms"):
        self.plugin_dir = Path(plugin_dir)
        self.plugins: Dict[str, Type] = {}
        self.observer: Optional[Observer] = None
        self._ensure_plugin_dir()
        
    def _ensure_plugin_dir(self):
        """Ensure the plugin directory exists."""
        self.plugin_dir.mkdir(parents=True, exist_ok=True)
        init_file = self.plugin_dir / "__init__.py"
        if not init_file.exists():
            init_file.touch()
            
    def discover_plugins(self) -> Dict[str, Type]:
        """Auto-discover all routing algorithm plugins."""
        logger.info(f"Discovering plugins in {self.plugin_dir}")
        self.plugins.clear()
        
        if not self.plugin_dir.exists():
            logger.warning(f"Plugin directory {self.plugin_dir} does not exist")
            return self.plugins
            
        # Scan for Python files
        for file_path in self.plugin_dir.glob("*.py"):
            if file_path.name.startswith("_"):
                continue
                
            try:
                module_name = file_path.stem
                plugin_class = self._load_plugin_module(file_path, module_name)
                
                if plugin_class:
                    self.plugins[module_name] = plugin_class
                    logger.info(f"Loaded plugin: {module_name}")
                    
            except Exception as e:
                logger.error(f"Failed to load plugin {file_path}: {e}")
                
        return self.plugins
        
    def _load_plugin_module(self, file_path: Path, module_name: str) -> Optional[Type]:
        """Load a single plugin module and extract the algorithm class."""
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        if spec is None or spec.loader is None:
            return None
            
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        
        # Look for a class that ends with 'Algorithm'
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if (isinstance(attr, type) and 
                attr_name.endswith('Algorithm') and 
                attr_name != 'RoutingAlgorithm'):
                return attr
                
        return None
        
    def get_plugin(self, name: str) -> Optional[Type]:
        """Get a plugin by name."""
        return self.plugins.get(name)
        
    def list_plugins(self) -> list:
        """List all available plugin names."""
        return list(self.plugins.keys())
        
    def reload_plugin(self, name: str) -> bool:
        """Reload a specific plugin."""
        try:
            file_path = self.plugin_dir / f"{name}.py"
            if not file_path.exists():
                logger.error(f"Plugin file {file_path} not found")
                return False
                
            plugin_class = self._load_plugin_module(file_path, name)
            if plugin_class:
                self.plugins[name] = plugin_class
                logger.info(f"Reloaded plugin: {name}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to reload plugin {name}: {e}")
            
        return False
        
    def enable_hot_reload(self):
        """Enable hot-reload for plugin files."""
        if self.observer is not None:
            logger.warning("Hot-reload already enabled")
            return
            
        event_handler = PluginFileHandler(self)
        self.observer = Observer()
        self.observer.schedule(event_handler, str(self.plugin_dir), recursive=False)
        self.observer.start()
        logger.info("Hot-reload enabled for plugins")
        
    def disable_hot_reload(self):
        """Disable hot-reload."""
        if self.observer:
            self.observer.stop()
            self.observer.join()
            self.observer = None
            logger.info("Hot-reload disabled")


class PluginFileHandler(FileSystemEventHandler):
    """Handle file system events for plugin hot-reload."""
    
    def __init__(self, loader: PluginLoader):
        self.loader = loader
        
    def on_modified(self, event):
        if event.is_directory or not event.src_path.endswith('.py'):
            return
            
        file_path = Path(event.src_path)
        plugin_name = file_path.stem
        
        if plugin_name.startswith('_'):
            return
            
        logger.info(f"Plugin file modified: {plugin_name}")
        self.loader.reload_plugin(plugin_name)
        
    def on_created(self, event):
        if event.is_directory or not event.src_path.endswith('.py'):
            return
            
        file_path = Path(event.src_path)
        plugin_name = file_path.stem
        
        if plugin_name.startswith('_'):
            return
            
        logger.info(f"New plugin file detected: {plugin_name}")
        self.loader.reload_plugin(plugin_name)


# Global plugin loader instance
_loader = None

def get_loader(plugin_dir: str = "src/plugins/algorithms") -> PluginLoader:
    """Get or create the global plugin loader instance."""
    global _loader
    if _loader is None:
        _loader = PluginLoader(plugin_dir)
        _loader.discover_plugins()
    return _loader
