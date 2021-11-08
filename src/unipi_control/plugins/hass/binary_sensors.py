import asyncio
import json
from dataclasses import asdict
from typing import Optional

from config import config
from config import LOG_MQTT_PUBLISH
from config import logger


class HassBinarySensorsDiscovery:
    def __init__(self, uc, mqtt_client):
        self.uc = uc
        self.mqtt_client = mqtt_client
        self.hardware = uc.neuron.hardware

    @staticmethod
    def _get_friendly_name(feature) -> str:
        friendly_name: str = f"{config.device_name} - {feature.circuit_name}"
        features_config: Optional[dict] = config.features.get(
            feature.circuit,
            {}
        )

        if features_config is not None:
            friendly_name = features_config.get("friendly_name", friendly_name)

        return friendly_name

    def _get_discovery(self, feature) -> tuple:
        topic: str = f"{config.homeassistant.discovery_prefix}/binary_sensor/{config.device_name.lower()}/{feature.circuit}/config"

        message: dict = {
            "name": self._get_friendly_name(feature),
            "unique_id": f"{config.device_name.lower()}_{feature.circuit}",
            "state_topic": f"{feature.topic}/get",
            "qos": 2,
            "device": {
                "name": config.device_name,
                "identifiers": config.device_name.lower(),
                "model":
                f"""{self.hardware["neuron"]["name"]} {self.hardware["neuron"]["model"]}""",
                "sw_version":
                self.uc.neuron.boards[feature._major_group - 1].firmware,
                **asdict(config.homeassistant.device),
            }
        }

        return topic, message

    async def publish(self) -> None:
        features = self.uc.neuron.features.by_feature_type(["DI"])

        for feature in features:
            topic, message = self._get_discovery(feature)
            json_data: str = json.dumps(message)
            logger.info(LOG_MQTT_PUBLISH, topic, json_data)
            await self.mqtt_client.publish(topic, json_data, qos=2)


class HassBinarySensorsMqttPlugin:
    def __init__(self, uc, mqtt_client):
        self.mqtt_client = mqtt_client
        self._hass = HassBinarySensorsDiscovery(uc, mqtt_client)

    async def init_task(self) -> set:
        tasks = set()

        task = asyncio.create_task(self._hass.publish())
        tasks.add(task)

        return tasks
