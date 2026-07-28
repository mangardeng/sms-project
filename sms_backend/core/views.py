from rest_framework.views import APIView
from rest_framework.response import Response


class PingView(APIView):

    def get(self, request):

        return Response({
            "message": "Authenticated successfully",
            "user": request.user.username,
            "role": request.user.role
        })