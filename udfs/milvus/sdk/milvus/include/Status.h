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

#include <string>

/**
 * @brief Milvus SDK namespace
 */
namespace milvus {

/**
 * @brief Status code for SDK interface return
 */
enum class StatusCode {
    OK = 0,

    // system error section
    UNKNOWN_ERROR = 1,
    NOT_SUPPORTED,
    NOT_CONNECTED,

    // function error section
    INVALID_AGUMENT = 1000,
    RPC_FAILED,
    SERVER_FAILED,
    TIMEOUT,

    // validation error
    DIMENSION_NOT_EQUAL = 2000,
    VECTOR_IS_EMPTY,
    JSON_PARSE_ERROR,
};

/**
 * @brief Status code and message returned by SDK interface.
 */
class Status {
 public:
    /**
     * @brief Constructor of Status
     */
    Status(StatusCode code, std::string msg);
    Status();

    /**
     * @brief A success status
     */
    static Status
    OK();

    /**
     * @brief Indicate the status is ok
     */
    bool
    IsOk() const;

    /**
     * @brief Return the status code
     */
    StatusCode
    Code() const;

    /**
     * @brief Return the error message
     */
    const std::string&
    Message() const;

 private:
    StatusCode code_{StatusCode::OK};
    std::string msg_{"OK"};
};  // Status

}  // namespace milvus
