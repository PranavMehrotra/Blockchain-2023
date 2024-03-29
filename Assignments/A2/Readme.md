# Hyperledger Fabric Network Setup Guide

This guide provides instructions for setting up a Hyperledger Fabric network using the `test-network` directory from the Fabric Samples repository.

## Prerequisites

Before you begin, ensure that you have the following prerequisites:

- Hyperledger Fabric Samples repository downloaded.
- Node.js installed on your system.
- Go 

## Installation

First, install the necessary Node.js packages by running the following commands in the terminal:

```bash
npm install fabric-ca-client
npm install fabric-network
```

## Network Setup
Navigate to the test-network directory: This directory is specified by the rootPath variable in the code.

- Change the rootPath variable in both the js files before running the code. rootPath should contain the path to test-network directory
- Start by bringing down any existing network:

```bash
./network.sh down
```

- Create a new network and channel:

```bash
./network.sh up createChannel -ca
```

- Deploy the Chaincode:
```bash
./network.sh deployCC -ccn basic -ccp <path-to-chaincode-implicit-directory> -ccl go -ccep "OR('Org1MSP.peer','Org2MSP.peer')"
```

## Running the Application

- Register admin and users for organization 1 and 2:
```bash
node multiuser.js
```
- To run the Node application for Org1/Org2:
This application is responsible for managing organization's interactions with the network.

```bash
node app.js
```

## Members:
- Pranav Mehrotra (20CS10085)
- Saransh Sharma (20CS30065)
- Shah Dhruv Rajendrabhai (20CS10088)
- Vivek Jaiswal (20CS10077)
