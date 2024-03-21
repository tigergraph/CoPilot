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
#include <map>
#include <string>

#include "../Status.h"
#include "DataType.h"

namespace milvus {

/**
 * @brief Field schema used by CollectionSchema
 */
class FieldSchema {
 public:
    FieldSchema();

    /**
     * @brief Constructor
     */
    FieldSchema(std::string name, DataType data_type, std::string description = "", bool is_primary_key = false,
                bool auto_id = false);

    /**
     * @brief Name of this field, cannot be empty.
     */
    const std::string&
    Name() const;

    /**
     * @brief Set name of the field.
     */
    void
    SetName(std::string name);

    /**
     * @brief Description of this field, can be empty.
     */
    const std::string&
    Description() const;

    /**
     * @brief Set description of the field.
     */
    void
    SetDescription(std::string description);

    /**
     * @brief Field data type.
     */
    DataType
    FieldDataType() const;

    /**
     * @brief Set field data type.
     */
    void
    SetDataType(DataType dt);

    /**
     * @brief The field is primary key or not.
     *
     * Each collection only has one primary key.
     * Currently only int64 type field can be primary key .
     */
    bool
    IsPrimaryKey() const;
    /**
     * @brief Set field to be primary key.
     */
    void
    SetPrimaryKey(bool is_primary_key);

    /**
     * @brief Field item's id is auto-generated or not.
     *
     * If ths flag is true, server will generate id when data is inserted.
     * Else the client must provide id for each entity when insert data.
     */
    bool
    AutoID() const;

    /**
     * @brief Set field item's id to be auto-generated.
     */
    void
    SetAutoID(bool auto_id);

    /**
     * @brief Extra key-value pair setting for this field
     *
     * Currently vector field need to input "dim":"x" to specify dimension.
     */
    const std::map<std::string, std::string>&
    TypeParams() const;

    /**
     * @brief Set extra key-value pair setting for this field
     *
     * Currently vector field need to input "dim":"x" to specify dimension.
     */
    void
    SetTypeParams(const std::map<std::string, std::string>& params);

    /**
     * @brief Set extra key-value pair setting for this field
     *
     * Currently vector field need to input "dim":"x" to specify dimension.
     */
    void
    SetTypeParams(std::map<std::string, std::string>&& params);

    /**
     * @brief Get dimension for a vector field
     */
    uint32_t
    Dimension() const;

    /**
     * @brief Quickly set dimension for a vector field
     */
    bool
    SetDimension(uint32_t dimension);

    /**
     * @brief Quickly set dimension for a vector field
     */
    FieldSchema&
    WithDimension(uint32_t dimension);

    /**
     * @brief Get max length for a varchar field
     */
    uint32_t
    MaxLength() const;

    /**
     * @brief Quickly set max length for a varchar field
     */
    void
    SetMaxLength(uint32_t length);

    /**
     * @brief Quickly set max length for a varchar field
     */
    FieldSchema&
    WithMaxLength(uint32_t length);

 private:
    std::string name_;
    std::string description_;
    DataType data_type_{DataType::FLOAT};
    bool is_primary_key_ = false;
    bool auto_id_ = false;
    std::map<std::string, std::string> type_params_;
};
}  // namespace milvus
