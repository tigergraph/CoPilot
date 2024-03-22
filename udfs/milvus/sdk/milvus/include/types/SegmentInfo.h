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
 * @brief State of segment
 */
enum class SegmentState {
    UNKNOWN = 0,
    NOT_EXIST = 1,
    GROWING = 2,
    SEALED = 3,
    FLUSHED = 4,
    FLUSHING = 5,
    DROPPED = 6,
};

/**
 * @brief Persisted segment information returned by MilvusClient::GetPersistentSegmentInfo().
 */
class SegmentInfo {
 public:
    /**
     * @brief Constructor
     */
    SegmentInfo(int64_t collection_id, int64_t partition_id, int64_t segment_id, int64_t row_count, SegmentState state);

    /**
     * @brief The collection id which this segment belong to.
     */
    int64_t
    CollectionID() const;

    /**
     * @brief The partition id which this segment belong to.
     */
    int64_t
    PartitionID() const;

    /**
     * @brief ID of the segment.
     */
    int64_t
    SegmentID() const;
    /**
     * @brief Row count of the segment.
     */
    int64_t
    RowCount() const;

    /**
     * @brief Current state of the segment.
     */
    SegmentState
    State() const;

 private:
    int64_t collection_id_{0};
    int64_t partition_id_{0};
    int64_t segment_id_{0};
    int64_t row_count_{0};

    SegmentState state_{SegmentState::UNKNOWN};
};

/**
 * @brief SegmentsInfo objects array
 */
using SegmentsInfo = std::vector<SegmentInfo>;

/**
 * @brief In-memory segment information returned by MilvusClient::GetQuerySegmentInfo().
 */
class QuerySegmentInfo : public SegmentInfo {
 public:
    /**
     * @brief Constructor
     */
    QuerySegmentInfo(int64_t collection_id, int64_t partition_id, int64_t segment_id, int64_t row_count,
                     SegmentState state, std::string index_name, int64_t index_id, int64_t node_id);

    /**
     * @brief Index name of the segment.
     */
    std::string
    IndexName() const;

    /**
     * @brief Index id the segment.
     */
    int64_t
    IndexID() const;

    /**
     * @brief Node id of the segment.
     */
    int64_t
    NodeID() const;

 private:
    std::string index_name_;
    int64_t index_id_{0};
    int64_t node_id_{0};
};

/**
 * @brief QuerySegmentsInfo objects array
 */
using QuerySegmentsInfo = std::vector<QuerySegmentInfo>;

}  // namespace milvus
