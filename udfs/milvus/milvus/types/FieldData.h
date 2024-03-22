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

#include <memory>
#include <vector>

#include "../Status.h"
#include "DataType.h"

namespace milvus {
class Field {
 public:
    /**
     * @brief Get field name
     */
    const std::string&
    Name() const;
    /**
     * @brief Get field data type
     */
    DataType
    Type() const;

    /**
     * @brief Total number of field elements
     */
    virtual size_t
    Count() const = 0;

 protected:
    Field(std::string name, DataType data_type);

 private:
    std::string name_;
    DataType data_type_;
};

using FieldDataPtr = std::shared_ptr<Field>;

/**
 * @brief Template class represents column-based data of a field. Available inheritance classes: \n
 *  BoolFieldData for boolean scalar field \n
 *  Int8FieldData for 8-bits integer scalar field \n
 *  Int16FieldData for 16-bits integer scalar field \n
 *  Int32FieldData for 32-bits integer scalar field \n
 *  Int64FieldData for 64-bits integer scalar field \n
 *  FloatFieldData for float scalar field \n
 *  DoubleFieldData for double scalar field \n
 *  VarCharFieldData for string scalar field (not supported in 2.0, reserved) \n
 *  BinaryVecFieldData for float vector scalar field \n
 *  FloatVecFieldData for binary vector scalar field \n
 */
template <typename T, DataType Dt>
class FieldData : public Field {
 public:
    /**
     * @brief Field element type
     */
    using ElementT = T;

    /**
     * @brief Constructor
     */
    FieldData();

    /**
     * @brief Constructor
     */
    explicit FieldData(std::string name);

    /**
     * @brief Constructor
     */
    FieldData(std::string name, const std::vector<T>& data);

    /**
     * @brief Constructor
     */
    FieldData(std::string name, std::vector<T>&& data);

    /**
     * @brief Add element to field data
     */
    virtual StatusCode
    Add(const T& element);

    /**
     * @brief Add element to field data
     */
    virtual StatusCode
    Add(T&& element);

    /**
     * @brief Total number of field elements
     */
    size_t
    Count() const final;

    /**
     * @brief Field elements array
     */
    virtual const std::vector<T>&
    Data() const;

    /**
     * @brief Field elements array
     */
    virtual std::vector<T>&
    Data();

 private:
    friend class BinaryVecFieldData;
    std::vector<T> data_;
};

class BinaryVecFieldData : public FieldData<std::string, DataType::BINARY_VECTOR> {
 public:
    /**
     * @brief Constructor
     */
    BinaryVecFieldData();

    /**
     * @brief Constructor
     */
    explicit BinaryVecFieldData(std::string name);

    /**
     * @brief Constructor
     */
    BinaryVecFieldData(std::string name, const std::vector<std::string>& data);

    /**
     * @brief Constructor
     */
    BinaryVecFieldData(std::string name, std::vector<std::string>&& data);

    /**
     * @brief Constructor
     */
    BinaryVecFieldData(std::string name, const std::vector<std::vector<uint8_t>>& data);

    /**
     * @brief Field elements array
     */
    const std::vector<std::string>&
    Data() const override;

    /**
     * @brief Field elements array
     */
    std::vector<std::string>&
    Data() override;

    /**
     * @brief Data export as uint8_t's vector
     */
    std::vector<std::vector<uint8_t>>
    DataAsUnsignedChars() const;

    /**
     * @brief Add element to field data
     */
    StatusCode
    Add(const std::string& element) override;

    /**
     * @brief Add element to field data
     */

    StatusCode
    Add(std::string&& element) override;

    /**
     * @brief Add element to field data
     */
    StatusCode
    Add(const std::vector<uint8_t>& element);

    /**
     * @brief Create binary vector strings from uint8_t vectors
     */
    static std::vector<std::string>
    CreateBinaryStrings(const std::vector<std::vector<uint8_t>>& data);

    /**
     * @brief Create binary vector string from uint8_t vector
     */
    static std::string
    CreateBinaryString(const std::vector<uint8_t>& data);
};

/**
 * @brief To test two FieldData are equal
 */
template <typename T, DataType Dt>
bool
operator==(const FieldData<T, Dt>& lhs, const FieldData<T, Dt>& rhs) {
    return lhs.Name() == rhs.Name() && lhs.Count() == rhs.Count() && lhs.Data() == rhs.Data();
}

/**
 * @brief To test two FieldData are equal
 */
template <typename T, DataType Dt>
bool
operator==(const FieldData<T, Dt>& lhs, const Field& rhs) {
    return lhs == dynamic_cast<const FieldData<T, Dt>&>(rhs);
}

using BoolFieldData = FieldData<bool, DataType::BOOL>;
using Int8FieldData = FieldData<int8_t, DataType::INT8>;
using Int16FieldData = FieldData<int16_t, DataType::INT16>;
using Int32FieldData = FieldData<int32_t, DataType::INT32>;
using Int64FieldData = FieldData<int64_t, DataType::INT64>;
using FloatFieldData = FieldData<float, DataType::FLOAT>;
using DoubleFieldData = FieldData<double, DataType::DOUBLE>;
using VarCharFieldData = FieldData<std::string, DataType::VARCHAR>;
using FloatVecFieldData = FieldData<std::vector<float>, DataType::FLOAT_VECTOR>;

using BoolFieldDataPtr = std::shared_ptr<BoolFieldData>;
using Int8FieldDataPtr = std::shared_ptr<Int8FieldData>;
using Int16FieldDataPtr = std::shared_ptr<Int16FieldData>;
using Int32FieldDataPtr = std::shared_ptr<Int32FieldData>;
using Int64FieldDataPtr = std::shared_ptr<Int64FieldData>;
using FloatFieldDataPtr = std::shared_ptr<FloatFieldData>;
using DoubleFieldDataPtr = std::shared_ptr<DoubleFieldData>;
using VarCharFieldDataPtr = std::shared_ptr<VarCharFieldData>;
using BinaryVecFieldDataPtr = std::shared_ptr<BinaryVecFieldData>;
using FloatVecFieldDataPtr = std::shared_ptr<FloatVecFieldData>;

extern template class FieldData<bool, DataType::BOOL>;
extern template class FieldData<int8_t, DataType::INT8>;
extern template class FieldData<int16_t, DataType::INT16>;
extern template class FieldData<int32_t, DataType::INT32>;
extern template class FieldData<int64_t, DataType::INT64>;
extern template class FieldData<float, DataType::FLOAT>;
extern template class FieldData<double, DataType::DOUBLE>;
extern template class FieldData<std::string, DataType::VARCHAR>;
extern template class FieldData<std::string, DataType::BINARY_VECTOR>;
extern template class FieldData<std::vector<float>, DataType::FLOAT_VECTOR>;

}  // namespace milvus
