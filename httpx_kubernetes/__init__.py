import socket
import functools as ft
import anyio.abc
import asyncio
import typing

from httpcore import AsyncNetworkBackend, AsyncNetworkStream, Request, Response, AsyncConnectionPool, AsyncConnectionPool
from httpx import AsyncHTTPTransport, Request, Response

from httpcore._backends.anyio import AnyIOStream

class KubernetesPortForwardStream(anyio.abc.SocketStream):
    def __init__(self, portforward, port) -> None:
        self._portforward = portforward
        self._port = port
        self._sock = portforward.socket(port)
        self._sock.setblocking(False)

    async def aclose(self):
        self._sock.close()

    async def send(self, item: bytes) -> None:
        loop = asyncio.get_running_loop()
        return await loop.sock_sendall(self._sock, item)

    async def receive(self, max_bytes: int = 65536) -> bytes:
        loop = asyncio.get_running_loop()
        return await loop.sock_recv(self._sock, max_bytes)

    async def send_eof(self) -> None:
        raise NotImplementedError

    @property
    def _raw_socket(self) -> socket.socket:
        return self._sock

class KubernetesPortForwardNetworkBackend(AsyncNetworkBackend):
    def __init__(self, api):
        self._api = api

    async def connect_tcp(
        self,
        host: str,
        port: int,
        timeout: typing.Optional[float] = None,
        local_address: typing.Optional[str] = None,
        socket_options: typing.Optional[typing.Iterable[typing.Any]] = None,
    ) -> AsyncNetworkStream:
        import kubernetes as kb
        loop = asyncio.get_running_loop()
        podname, namespace = host.split('.')
        pf = await loop.run_in_executor(
            None,
            ft.partial(
                kb.stream.portforward,
                self._api.connect_get_namespaced_pod_portforward,
                name=podname,
                namespace=namespace,
                ports=str(port),
            )
        )
        return AnyIOStream(stream=KubernetesPortForwardStream(pf, port))


class KubernetesTransport(AsyncHTTPTransport):
    def __init__(
            self, 
            *,
            api=None,
            context=None,
    ):
        if api is None:
            import kubernetes as kb
            api = kb.client.CoreV1Api(api_client=kb.config.new_client_from_config(context=context))
        elif context is not None:
            raise ValueError('Only one of (api, context) must be provided.')

        self._pool = AsyncConnectionPool(network_backend=KubernetesPortForwardNetworkBackend(api=api))

    async def handle_async_request(self, request: Request) -> Response:
        # fake the scheme because super() doesn't like unknown shcemes
        request.url = request.url.copy_with(scheme='http')
        return await super().handle_async_request(request)
