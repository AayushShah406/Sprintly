from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from .broker import event_broker

class ScalabilityTelemetryView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        telemetry = event_broker.get_telemetry()
        return Response(telemetry)


class SimulateEventView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        topic = request.data.get("topic", "sprintly.issues.lifecycle")
        event_type = request.data.get("event_type", "LOAD_SPIKE_EVENT")
        payload = request.data.get("payload", {"batch_size": 25, "source": "StressTestWorker"})
        actor = request.data.get("actor", "LoadTester")

        msg = event_broker.publish(topic=topic, event_type=event_type, payload=payload, actor=actor)
        return Response({
            "message": "Event successfully published to Kafka/RabbitMQ pipeline.",
            "event": msg,
        })
