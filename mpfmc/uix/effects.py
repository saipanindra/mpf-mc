import importlib
import abc
from typing import TYPE_CHECKING, Optional, List, Union

from kivy.event import EventDispatcher
from kivy.uix.effectwidget import (MonochromeEffect, InvertEffect,
                                   ScanlinesEffect, ChannelMixEffect,
                                   PixelateEffect, HorizontalBlurEffect,
                                   VerticalBlurEffect, FXAAEffect,
                                   EffectBase)

if TYPE_CHECKING:
    from mpfmc.core.mc import MpfMc


class EffectsManager(object):
    def __init__(self, mc: "MpfMc") -> None:
        self.mc = mc
        self._effects = dict()
        self._register_mpf_effects()
        self._register_kivy_effects()

    @property
    def effects(self) -> dict:
        return self._effects

    def register_effect(self, name: str, transition_cls) -> None:
        self._effects[name] = transition_cls

    def get_effect(self, config: Optional[dict]=None) -> List["EffectBase"]:
        if config:
            # The kivy shader transitions can't accept unexpected kwargs
            kwargs = config.copy()
            effect_obj = self._effects[config['type']]()

            # Set effect properties
            for attr, value in kwargs.items():
                if hasattr(effect_obj, attr):
                    setattr(effect_obj, attr, value)

            if isinstance(effect_obj, EffectBase):
                return [effect_obj]
            elif isinstance(effect_obj, EffectsChain):
                return effect_obj.get_effects()
            else:
                return []
        else:
            return []

    def _register_mpf_effects(self) -> None:
        for t in self.mc.machine_config['mpf-mc']['mpf_effect_modules']:
            i = importlib.import_module('mpfmc.effects.{}'.format(t))
            self.register_effect(getattr(i, 'name'),
                                 getattr(i, 'effect_cls'))

    def _register_kivy_effects(self) -> None:
        self.register_effect('invert_colors', InvertEffect)
        self.register_effect('scanlines', ScanlinesEffect)
        self.register_effect('color_channel_mix', ChannelMixEffect)
        self.register_effect('pixelate', PixelateEffect)
        self.register_effect('horizontal_blur', HorizontalBlurEffect)
        self.register_effect('vertical_blur', VerticalBlurEffect)
        self.register_effect('anti_aliasing', FXAAEffect)

    def validate_effects(self, config: Union[dict, list]) -> list:
        """
        Validate the effects section of a widget.
        
        Args:
            config: The localized 'effects' config dictionary for a single widget. 

        Returns:
            A list of 'effects' config dictionary entries that have been validated.
        """
        if isinstance(config, dict):
            config = [config]

        effect_list = list()

        for effect in config:
            effect_list.append(self.process_effect(effect))

        return effect_list

    def process_effect(self, config: dict) -> dict:
        try:
            effect_cls = self._effects[config['type']]
        except (KeyError, TypeError):
            try:
                raise ValueError(
                    '"{}" is not a valid MPF widget effect type. Did you '
                    'misspell it, or forget to enable it in the "mpf-mc: '
                    'mpf_effect_modules" section of your machine config?'.format(
                        config['type']))
            except (KeyError, TypeError):
                raise ValueError("Invalid widget effects config: {}".format(config))

        self.mc.config_validator.validate_config('effects:{}'.format(
            config['type']).lower(), config, base_spec='effects:common')

        return config


class EffectsChain(EventDispatcher, metaclass=abc.ABCMeta):
    """Abstract base class for an effect that is actually a chain of 
    one or more individual effects."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @abc.abstractmethod
    def get_effects(self) -> List["EffectBase"]:
        """Return the list of effects in this chain."""
        raise NotImplementedError('get_effects method must be defined to use this base class')
