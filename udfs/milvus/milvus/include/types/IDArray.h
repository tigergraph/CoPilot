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
#include <vector>

namespace milvus {

/**
 * @brief ID array, each ID could be int64 type or string type. \n
 * Note: v2.0 only support int64 type id.
 */
class IDArray {
 public:
    /**
     * @brief Constructor
     */
    explicit IDArray(const std::vector<int64_t>& id_array);

    /**
     * @brief Constructor
     */
    explicit IDArray(std::vector<int64_t>&& id_array);

    /**
     * @brief Constructor
     */
    explicit IDArray(const std::vector<std::string>& id_array);

    /**
     * @brief Constructor
     */
    explicit IDArray(std::vector<std::string>&& id_array);

    /**
     * @brief Indicate this is an integer id array
     */
    bool
    IsIntegerID() const;

    /**
     * @brief Return integer id array
     */
    const std::vector<int64_t>&
    IntIDArray() const;

    /**
     * @brief Return string id array
     */
    const std::vector<std::string>&
    StrIDArray() const;

 private:
    bool is_int_array_{true};
    std::vector<int64_t> int_id_array_;
    std::vector<std::string> str_id_array_;
};

}  // namespace milvus
