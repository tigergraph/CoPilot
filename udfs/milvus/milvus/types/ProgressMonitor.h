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
#include <functional>
#include <limits>

namespace milvus {

/**
 * @brief Notify progress of a request, returned by callback function of ProgressMonitor
 */
struct Progress {
    Progress();

    /**
     * @brief Constructor
     */
    Progress(uint32_t finished, uint32_t total);

    /**
     * @brief The progress is done or not
     */
    bool
    Done() const;

    /**
     * @brief How much work is finished
     */
    uint32_t finished_ = 0;

    /**
     * @brief Totally how much work it is
     */
    uint32_t total_ = 0;
};

/**
 * @brief To test two Progress are equal
 */
bool
operator==(const Progress& a, const Progress& b);

/**
 * @brief Monitor progress of a request
 */
class ProgressMonitor {
 public:
    /**
     * @brief The call back function definition to receive progress notification
     */
    using CallbackFunc = std::function<void(Progress&)>;

    /**
     * @brief Constructor to set time duration to wait the progress complete.
     *
     * @param [in] check_timeout set the value to controls the time duration to wait the progress. Unit: second.
     */
    explicit ProgressMonitor(uint32_t check_timeout);

    /**
     * @brief Default progress setting. Default timeout value: 60 seconds.
     */
    ProgressMonitor();

    /**
     * @brief time duration to wait the progress complete.
     */
    uint32_t
    CheckTimeout() const;

    /**
     * @brief time interval to check the progress state.
     */
    uint32_t
    CheckInterval() const;

    /**
     * @brief Set time interval to check the progress state.
     *
     * @param [in] check_interval set value to controls the time interval to
     * check progress state. Unit: millisecond. Default value: 500 milliseconds.
     */
    void
    SetCheckInterval(uint32_t check_interval);

    /**
     * @brief Trigger the call back function to notify progress
     */
    void
    DoProgress(Progress& p) const;

    /**
     * @brief Set call back function to receive progress notification.
     *
     * @param [in] func call back function to receive progress notification.
     */
    void
    SetCallbackFunc(CallbackFunc func);

    /**
     * @brief Immediately return without waiting request finished
     */
    static ProgressMonitor
    NoWait();

    /**
     * @brief A monitor to wait request until it is finished
     */
    static ProgressMonitor
    Forever();

 private:
    uint32_t check_interval_{500};
    uint32_t check_timeout_{60};

    std::function<void(Progress&)> callback_func_;
};
}  // namespace milvus
