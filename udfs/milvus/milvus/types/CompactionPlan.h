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

namespace milvus {

/**
 * @brief Compaction plan information. Used by MilvusClient::GetCompactionPlans().
 */
class CompactionPlan {
 public:
    /**
     * @brief Construct a new Compaction Plan object
     *
     */
    CompactionPlan();

    /**
     * @brief Constructor
     */
    CompactionPlan(const std::vector<int64_t>& segments, int64_t dst_segment);

    /**
     * @brief Constructor
     */
    CompactionPlan(std::vector<int64_t>&& segments, int64_t dst_segment);

    /**
     * @brief Segment id array to be merged.
     */
    const std::vector<int64_t>&
    SourceSegments() const;

    /**
     * @brief Set segment id array to be merged.
     */
    void
    SetSourceSegments(const std::vector<int64_t>& segments);

    /**
     * @brief Set segment id array to be merged.
     */
    void
    SetSourceSegments(std::vector<int64_t>&& segments);

    /**
     * @brief New generated segment id after merging.
     */
    int64_t
    DestinySegemnt() const;

    /**
     * @brief Set segment id.
     */
    void
    SetDestinySegemnt(int64_t id);

 private:
    std::vector<int64_t> src_segments_;
    int64_t dst_segment_ = 0;
};

/**
 * @brief CompactionPlans objects array
 */
using CompactionPlans = std::vector<CompactionPlan>;

}  // namespace milvus
