# Лабораторная работа №2 - Kubernetes


## Часть 1

В качестве сервиса я решил взять страницу с пикми-надписью "Эта веб-страница просто ✨чудесна✨" шрифтом lobster.


Для этого я создал `configmap.yaml`, который содержит `index.html` файл веб-страницы. Он передаст этот файл в контейнеры.
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: web-content
data:
  index.html: |
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>lobster</title>
        <link href="https://fonts.googleapis.com/css2?family=Lobster&display=swap" rel="stylesheet">
        <style>
            body {
                display: flex;
                justify-content: center;
                align-items: center;
                height: 100vh;
                font-size: 2rem;
                font-family: 'Lobster', cursive;
            }
        </style>
    </head>
    <body>
        Эта веб-страница просто ✨чудесна✨
    </body>
    </html>
```

В `deployment.yaml` я описал контейнер nginx, который должен поднимать веб-страницу из ConfigMap.

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: lobster-web
spec:
  replicas: 1
  selector:
    matchLabels:
      app: lobster-web
  template:
    metadata:
      labels:
        app: lobster-web
    spec:
      containers:
        - name: nginx
          image: nginx:stable
          ports:
            - containerPort: 80
          volumeMounts:
            - name: html
              mountPath: /usr/share/nginx/html
      volumes:
        - name: html
          configMap:
            name: web-content
```

Наконец, `service.yaml` обеспечивает доступ по порту 30080.

```yaml
apiVersion: v1
kind: Service
metadata:
  name: lobster-web-service
spec:
  type: NodePort
  selector:
    app: lobster-web
  ports:
    - port: 80
      targetPort: 80
      nodePort: 30080
```

Запускаем minikube, применяем файлы и поднимаем сервис:

```bash
minikube start
kubectl apply -f .
minikube service lobster-web-service
```

![веб-страница](screenshots/lobster1.png)


## Часть 2


С помощью команд
```bash
helm create lobster-web
cd lobster-web
```
я создал шаблон для helm chart.
В файл `values.yaml` я изиенил `type` в `service` на NodePort, добавил значение `nodePort`
Также я добавил в значение `html` содержимое веб-страницы.
В конце файла содержатся закомментированные `volumes` и `volumeMounts`, я подставил туда свои значения из прошлого `deployment.yaml`.

Ещё я добавил в template файл `configmap.yaml`
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: {{ .Release.Name }}-config
data:
  index.html: |
{{ .Values.html | indent 4 }}
```

Затем я запустил release
```sh
helm install lobster-release .
```
![lens release](screenshots/lens.png)
На скриншоте release в IDE Lens. Здесь же можно изменить файл `values.yaml`, сохранить его и обновить release с помощью кнопки upgrade.

Для примера я изменил порт с 30800 на 30801:
![port](screenshots/port.png)

## А минусы будут?

1. Все измменения можно производить в одном файле `values.yaml`, не трогая остальные файлы
2. С помощью одной команды (или кнопки в IDE) все изменения применятся к остальным файлам автоматически
3. Не нужно отдельно прописывать `kubectl apply` для всех манифестов
4. История версий для легкого отката в случае ошибки

Подводя итог, автоматизация - маст хев!