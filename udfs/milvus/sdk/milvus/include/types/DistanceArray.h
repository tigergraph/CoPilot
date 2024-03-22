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
 * @brief 2-d array distances returned by MilvusClient::CalcDistance(), each distance could be int type or float type.
 * \n
 * Note: std::vector<std::vector<int>> for "HAMMING" or std::vector<std::vector<float>> for others.
 */
class DistanceArray {
 public:
    /**
     * @brief Constructor
     */
    DistanceArray();

    /**
     * @brief Constructor
     */
    explicit DistanceArray(const std::vector<std::vector<int32_t>>& distance_array);

    /**
     * @brief Constructor
     */
    explicit DistanceArray(std::vector<std::vector<int32_t>>&& distance_array);

    /**
     * @brief Constructor
     */
    explicit DistanceArray(const std::vector<std::vector<float>>& distance_array);

    /**
     * @brief Constructor
     */
    explicit DistanceArray(std::vector<std::vector<float>>&& distance_array);

    /**
     * @brief Test the distance is float or integer
     */
    bool
    IsIntegerDistance() const;

    /**
     * @brief Integer distance 2-d array.
     *        Assume the vectors_left: L_1, L_2, L_3 \n
     *        Assume the vectors_right: R_a, R_b \n
     *        Distance between L_n and R_m we called "D_n_m" \n
     *        The returned distances are arranged like this: [[D_1_a, D_1_b], [D_2_a, D_2_b], [D_3_a, D_3_b]]
     *
     */
    const std::vector<std::vector<int32_t>>&
    IntDistanceArray() const;

    /**
     * @brief Set integer distance array
     */
    void
    SetIntDistance(const std::vector<std::vector<int32_t>>& distance_array);

    /**
     * @brief Set integer distance array
     */
    void
    SetIntDistance(std::vector<std::vector<int32_t>>&& distance_array);

    /**
     * @brief Float distance 2-d array we called.
     *        Assume the vectors_left: L_1, L_2, L_3 \n
     *        Assume the vectors_right: R_a, R_b \n
     *        Distance between L_n and R_m we called "D_n_m" \n
     *        The returned distances are arranged like this: [[D_1_a, D_1_b], [D_2_a, D_2_b], [D_3_a, D_3_b]]
     */
    const std::vector<std::vector<float>>&
    FloatDistanceArray() const;

    /**
     * @brief Set float distance array
     */
    void
    SetFloatDistance(const std::vector<std::vector<float>>& distance_array);

    /**
     * @brief Set float distance array
     */
    void
    SetFloatDistance(std::vector<std::vector<float>>&& distance_array);

 private:
    bool is_int_distance_{false};
    std::vector<std::vector<int32_t>> int_array_;
    std::vector<std::vector<float>> float_array_;
};

}  // namespace milvus
