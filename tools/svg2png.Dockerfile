FROM python:3.11-slim

# Install Cairo and deps required by cairosvg/cairocffi
RUN apt-get update \
     && apt-get install -y --no-install-recommends \
         libcairo2 \
         libpango-1.0-0 \
         libgdk-pixbuf-xlib-2.0-0 \
         libffi8 \
         pkg-config \
         build-essential \
         ca-certificates \
     && rm -rf /var/lib/apt/lists/*

RUN python -m pip install --upgrade pip
RUN python -m pip install cairosvg

WORKDIR /work

CMD ["python", "-c", "import cairosvg; cairosvg.svg2png(url='/work/docs/deployment.svg', write_to='/work/docs/deployment.png')"]
