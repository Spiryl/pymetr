import logging
logger = logging.getLogger(__name__)
from enum import Enum
from collections.abc import Iterable
from PySide6.QtCore import QObject, Signal
import logging

class Sources(QObject):
    """
    Handles the management and operation of sources for SCPI instruments.

    Attributes:
        source_changed (Signal): Emitted when the list of active sources changes.
    """

    source_changed = Signal(list)

    def __init__(self, sources):
        """
        Initializes the Sources object with the available sources.

        Args:
            sources (list): List of available sources.
        """
        super().__init__()
        self._sources = [source.value if isinstance(source, Enum) else source for source in sources]
        self._source = []
        logger.info("Sources initialized with: %s", self._sources)

    @property
    def source(self):
        """
        Returns the list of active sources.

        Returns:
            list: Active sources.
        """
        return self._source

    @source.setter
    def source(self, sources):
        """
        Sets the active sources from the available sources.

        Args:
            sources (list): List of sources to set as active.
        """
        self._source = [source for source in sources if source in self._sources]
        logger.debug("Active source set to: %s", self._source)
        self.source_changed.emit(self._source)

    @property
    def sources(self):
        """
        Returns the list of available sources.

        Returns:
            list: Available sources.
        """
        return self._sources

    def add_source(self, source):
        """
        Adds a source to the list of active sources if it's available and not already active.

        Args:
            source (str or Enum): Source to add to the active sources.
        """
        source = source.value if isinstance(source, Enum) else source
        if source in self._sources and source not in self._source:
            self._source.append(source)
            logger.info("Added active source: %s", source)
            self.source_changed.emit(self._source)

    def remove_source(self, source):
        """
        Removes a source from the list of active sources if it's currently active.

        Args:
            source (str or Enum): Source to remove from the active sources.
        """
        source = source.value if isinstance(source, Enum) else source
        if source in self._source:
            self._source.remove(source)
            logger.info("Removed active source: %s", source)
            self.source_changed.emit(self._source)

    def set_sources(self, sources):
        """
        Sets the list of active sources from the available sources.

        Args:
            sources (list): List of sources to set as active.
        """
        self._source = [source.value if isinstance(source, Enum) else source for source in sources if source in self._sources]
        logger.debug("Active sources set to: %s", self._source)
        self.source_changed.emit(self._source)

    @staticmethod
    def source_command(command_template=None, formatter=None, single=False, join_str=', '):
        """
        Decorator for source-related commands.

        The `source_command` decorator is used to handle source-related commands in a flexible manner.
        It allows you to specify a command template, source formatting, and whether to handle sources
        individually or collectively.

        Usage Examples:
            @Sources.source_command(":DIGitize {}", single=True)
            def digitize(self, source):
                # Digitizes the specified source individually.
                pass

            @Sources.source_command(":calculate:measurement {}", formatter="'{}'", join_str=', ')
            def calculate_measurement(self, *sources):
                # Calculates the measurement for the specified sources.
                pass

            @Sources.source_command(single=True)
            def custom_function_single(self, source):
                # Performs a custom operation on each source individually.
                pass

            @Sources.source_command()
            def custom_function_multi(self, *sources):
                # Performs a custom operation on multiple sources.
                pass

        Args:
            command_template (str, optional): Template for the SCPI command. Defaults to None.
            formatter (str, optional): Formatter for the sources. Defaults to None.
            single (bool, optional): Whether to handle sources individually. Defaults to False.
            join_str (str, optional): String to join multiple sources. Defaults to ', '.

        Returns:
            function: Decorated function.
        """
        def decorator(func):
            def wrapper(self, *args, **kwargs):
                sources_to_use = self.sources.source if not args else args

                if isinstance(sources_to_use, Enum):
                    sources_to_use = [sources_to_use]
                elif not isinstance(sources_to_use, Iterable) or isinstance(sources_to_use, str):
                    sources_to_use = [sources_to_use]

                cleaned_sources = [source.value if isinstance(source, Enum) else source for source in sources_to_use]

                if formatter:
                    cleaned_sources = [formatter.format(source) for source in cleaned_sources]

                if command_template:
                    if single:
                        for source in cleaned_sources:
                            command = command_template.format(source)
                            logger.debug(f"Executing command: {command}")
                            self.write(command)
                            func(self, source, **kwargs)
                    else:
                        command = command_template.format(join_str.join(cleaned_sources))
                        logger.debug(f"Executing command: {command}")
                        self.write(command)
                        return func(self, *cleaned_sources, **kwargs)
                else:
                    if single:
                        for source in cleaned_sources:
                            func(self, source, **kwargs)
                    else:
                        return func(self, *cleaned_sources, **kwargs)

            return wrapper
        return decorator
    