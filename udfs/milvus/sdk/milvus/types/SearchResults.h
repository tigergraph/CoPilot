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
#include <vector>

#include "FieldData.h"
#include "IDArray.h"

namespace milvus {

/**
 * @brief Topk results for one target vector of MilvusClient::Search()
 */
struct SingleResult {
    /**
     * @brief Constructor
     */
    SingleResult(IDArray&& ids, std::vector<float>&& scores, std::vector<FieldDataPtr>&& output_fields);

    /**
     * @brief Distances/scores array of one target vector
     */
    const std::vector<float>&
    Scores() const;

    /**
     * @brief Topk id array of one target vector
     */
    const IDArray&
    Ids() const;

    /**
     * @brief Output fields data
     */
    const std::vector<FieldDataPtr>&
    OutputFields() const;

    /**
     * @brief Get an output field by name
     */
    FieldDataPtr
    OutputField(const std::string& name) const;

 private:
    IDArray ids_;
    std::vector<float> scores_;
    std::vector<FieldDataPtr> output_fields_;
};

/**
 * @brief Results returned by MilvusClient::Search().
 */
class SearchResults {
 public:
    SearchResults();

    /**
     * @brief Constructor
     */
    explicit SearchResults(std::vector<SingleResult>&& results);

    /**
     * @brief Get search results.
     */
    std::vector<SingleResult>&
    Results();

 private:
    std::vector<SingleResult> nq_results_{};
};

}  // namespace milvus
