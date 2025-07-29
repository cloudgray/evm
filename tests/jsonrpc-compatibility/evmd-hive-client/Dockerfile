FROM golang:1.23-alpine AS builder

# Install required packages
RUN apk add --update git ca-certificates gcc musl-dev linux-headers make

# Clone the cosmos/evm repository
# Note: You may need to adjust this URL or use a specific branch/tag
WORKDIR /workspace
RUN git clone https://github.com/cosmos/evm.git .

# Build evmd binary
WORKDIR /workspace/evmd
RUN go mod download
RUN go build -v -o evmd ./cmd/evmd

# Build the final image
FROM alpine:latest
RUN apk add --update bash curl jq python3

# Copy evmd binary from builder
COPY --from=builder /workspace/evmd/evmd /usr/local/bin/evmd

# Generate the version.txt file
RUN echo "evmd/v1.0.0" > /version.txt

# Inject the startup script and genesis converter
ADD evmd.sh /evmd.sh
ADD mapper.jq /mapper.jq
ADD genesis_converter.py /genesis_converter.py
ADD add_hive_accounts.py /add_hive_accounts.py
RUN chmod +x /evmd.sh

# Inject the enode id retriever script (create a placeholder for now)
RUN mkdir /hive-bin
ADD enode.sh /hive-bin/enode.sh
RUN chmod +x /hive-bin/enode.sh

# Add a default genesis file
ADD genesis.json /genesis.json

# Export the usual networking ports to allow outside access to the node
EXPOSE 8545 8546 8547 8551 30303 30303/udp

ENTRYPOINT ["/evmd.sh"]