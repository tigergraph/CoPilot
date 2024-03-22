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

namespace milvus {

/**
 * @brief Supported index types.
 */
enum class IndexType {
    INVALID = 0,
    FLAT,
    IVF_FLAT,
    IVF_SQ8,
    IVF_PQ,
    HNSW,
    IVF_HNSW,
    RHNSW_FLAT,
    RHNSW_SQ,
    RHNSW_PQ,
    ANNOY,

    BIN_FLAT = 1001,
    BIN_IVF_FLAT,
};
}  // namespace milvus
