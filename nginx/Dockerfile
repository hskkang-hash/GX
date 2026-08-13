FROM nginx:alpine

RUN rm /etc/nginx/conf.d/default.conf
COPY nginx.conf /etc/nginx/nginx.conf
RUN mkdir -p /media

EXPOSE 3002
EXPOSE 8002

CMD ["nginx", "-g", "daemon off;"] 