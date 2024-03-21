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
 * @brief Partition runtime information including create timestamp and loading percentage, returned by
 * MilvusClient::ShowPartitions().
 */
class PartitionInfo {
 public:
    /**
     * @brief Constructor
     */
    PartitionInfo(std::string name, int64_t id, uint64_t created_utc_timestamp = 0, int64_t in_memory_percentage = 0);

    /**
     * @brief Get name of this partition.
     */
    std::string
    Name() const;

    /**
     * @brief Get internal id of this partition.
     */
    int64_t
    Id() const;

    /**
     * @brief Get the utc timestamp calculated by created_timestamp.
     */
    uint64_t
    CreatedUtcTimestamp() const;

    /**
     * @brief Get partition loading percentage.
     */
    int64_t
    InMemoryPercentage() const;

    /**
     * @brief Indicated whether the partition has been loaded completed.
     */
    bool
    Loaded() const;

 private:
    std::string name_;
    int64_t id_{0};
    uint64_t created_utc_timestamp_{0};
    int64_t in_memory_percentage_ = {0};
};

/**
 * @brief To test two PartitionInfo are equal
 */
bool
operator==(const PartitionInfo& a, const PartitionInfo& b);

/**
 * @brief PartitionsInfo objects array
 */
using PartitionsInfo = std::vector<PartitionInfo>;

}  // namespace milvus
