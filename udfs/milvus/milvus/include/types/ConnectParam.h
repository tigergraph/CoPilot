// Licensed to the LF AI & Data foundation under one
// or more contributor license agreements. See the NOTICE file
// distributed with this work for additional information
// regarding copyright ownership. The ASF licenses this file
// to you under the Apache License, Version 2.0 (the
// "License"); you may not use this file except in compliance
// with the License. You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

#pragma once

#include <cstdint>
#include <string>

namespace milvus {

/**
 * @brief Connection parameters. Used by MilvusClient::Connect()
 */
class ConnectParam {
 public:
    /**
     * @brief Constructor
     */
    ConnectParam(std::string host, uint16_t port);

    /**
     * @brief Constructor
     */
    ConnectParam(std::string host, uint16_t port, std::string username, std::string password);

    /**
     * @brief IP of the milvus proxy.
     */
    const std::string&
    Host() const;

    /**
     * @brief Port of the milvus proxy.
     */
    uint16_t
    Port() const;

    /**
     * @brief Uri for connecting to the milvus.
     */
    std::string
    Uri() const;

    /**
     * @brief Authorizations header value for connecting to the milvus.
     * Authorizations() = base64('username:password')
     */
    const std::string&
    Authorizations() const;

    /**
     * @brief SetAuthorizations set username and password for connecting to the milvus.
     */
    void
    SetAuthorizations(std::string username, std::string password);

    /**
     * @brief Connect timeout in milliseconds.
     *
     */
    uint32_t
    ConnectTimeout() const;

    /**
     * @brief Set connect timeout in milliseconds.
     *
     */
    void
    SetConnectTimeout(uint32_t timeout);

    /**
     * @brief With ssl
     */
    ConnectParam&
    WithTls();

    /**
     * @brief Enable ssl
     */
    void
    EnableTls();

    /**
     * @brief With ssl
     */
    ConnectParam&
    WithTls(const std::string& server_name, const std::string& ca_cert);

    /**
     * @brief Enable ssl
     */
    void
    EnableTls(const std::string& server_name, const std::string& ca_cert);

    /**
     * @brief With ssl and provides certificates
     */
    ConnectParam&
    WithTls(const std::string& server_name, const std::string& cert, const std::string& key,
            const std::string& ca_cert);

    /**
     * @brief Enable ssl and provides certificates
     */
    void
    EnableTls(const std::string& server_name, const std::string& cert, const std::string& key,
              const std::string& ca_cert);

    /**
     * @brief Disable ssl
     */
    void
    DisableTls();

    /**
     * @brief TlsEnabled
     */
    bool
    TlsEnabled() const;

    /**
     * @brief ServerName tls hostname
     */
    const std::string&
    ServerName() const;

    /**
     * @brief Cert tls cert file
     */
    const std::string&
    Cert() const;

    /**
     * @brief Key tls key file
     */
    const std::string&
    Key() const;

    /**
     * @brief CaCert tls ca cert file
     */
    const std::string&
    CaCert() const;

 private:
    std::string host_;
    uint16_t port_ = 0;
    uint32_t connect_timeout_ = 5000;

    bool tls_{false};
    std::string server_name_;
    std::string cert_;
    std::string key_;
    std::string ca_cert_;

    std::string authorizations_;
};

}  // namespace milvus
