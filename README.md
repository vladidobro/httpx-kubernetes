Httpx transport for Kubernetes
==============================

This is a plugin for the [next generation HTTP client for Python](https://github.com/encode/httpx) that makes it possible to easily connect
to local ports on pods in kubernetes, similar to `kubectl port-forward`.

Example:
```
import httpx
from httpx_kubernetes import KubernetesPortForwardTransport

mounts = {'kube://': KubernetesPortForwardTransport(context='mycontext')
# alternatively, create the CoreV1Api and pass it as 'api' keyword argument

async with httpx.AsyncClient(mounts=mounts) as c:
    response = await c.get('kube://podname.namespace:80/index.html')
```

Feel free to copy this code in your project to avoid dependency.
