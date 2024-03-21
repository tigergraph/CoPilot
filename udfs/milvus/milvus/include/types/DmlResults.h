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
#include <vector>

#include "IDArray.h"

namespace milvus {

/**
 * @brief Result returned by MilvusClient::Insert() and MilvusClient::Delete()
 */
class DmlResults {
 public:
    /**
     * @brief The id array for entities which are inserted or deleted.
     */
    const IDArray&
    IdArray() const;

    /**
     * @brief Set the id array.
     */
    void
    SetIdArray(const IDArray& id_array);

    /**
     * @brief Set the id array.
     */
    void
    SetIdArray(IDArray&& id_array);

    /**
     * @brief The operation timestamp marked by server side.
     */
    uint64_t
    Timestamp() const;

    /**
     * @brief Set operation timestamp.
     */
    void
    SetTimestamp(uint64_t timestamp);

 private:
    IDArray id_array_{std::vector<int64_t>{}};
    uint64_t timestamp_{0};
};

}  // namespace milvus
