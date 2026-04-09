document.addEventListener("DOMContentLoaded", function() {
    const dashboardSearch = document.getElementById("dashboardBankSearch");
    const dashboardBanks = document.querySelectorAll("[data-bank-name]");
    const dashboardShell = document.querySelector(".dashboard-shell");
    const dashboardAccessMessage = document.getElementById("dashboardAccessMessage");
    const requiresLoginItems = document.querySelectorAll("[data-requires-login='true']");
    const requiresBankLinkItems = document.querySelectorAll("[data-requires-bank-link='true']");
    const scrollTargetItems = document.querySelectorAll("[data-scroll-target]");
    const bankNavigationItems = document.querySelectorAll("[data-bank-url]");
    const isDashboardAuthenticated = dashboardShell && dashboardShell.dataset.userAuthenticated === "true";
    const bankVerifyShell = document.querySelector(".bank-verify-shell");
    const bankVerifyStatus = document.getElementById("bankVerifyStatus");
    const bankVerifyEmail = document.getElementById("bankVerifyEmail");
    const bankVerifyOtp = document.getElementById("bankVerifyOtp");
    const sendBankOtpButton = document.getElementById("sendBankOtpButton");
    const verifyBankOtpButton = document.getElementById("verifyBankOtpButton");
    const numericOnlyInputs = document.querySelectorAll("[data-numeric-only='true']");
    const expiryInputs = document.querySelectorAll("[data-expiry-input='true']");
    const balanceToggle = document.querySelector("[data-balance-toggle='true']");
    const balancePanel = document.querySelector("[data-balance-panel='true']");
    const paymentToggle = document.querySelector("[data-payment-toggle='true']");
    const paymentPanel = document.querySelector("[data-payment-panel='true']");
    const requestRecipientInput = document.querySelector("[data-request-recipient-input='true']");
    const requestRecipientName = document.querySelector("[data-request-recipient-name='true']");
    const recentRequestContacts = document.querySelectorAll("[data-request-recipient]");
    const overviewDataScript = document.getElementById("dashboardOverviewData");
    const qrDownloadButton = document.querySelector("[data-qr-download='true']");
    const qrShareButton = document.querySelector("[data-qr-share='true']");

    if (dashboardSearch && dashboardBanks.length) {
        dashboardSearch.addEventListener("input", function() {
            const term = dashboardSearch.value.trim().toLowerCase();

            dashboardBanks.forEach(function(bank) {
                const bankName = bank.dataset.bankName || "";
                const isVisible = !term || bankName.includes(term);

                bank.style.display = isVisible ? "" : "none";
            });
        });
    }

    if (requiresLoginItems.length && !isDashboardAuthenticated) {
        requiresLoginItems.forEach(function(item) {
            item.addEventListener("click", function(event) {
                event.preventDefault();

                if (dashboardAccessMessage) {
                    dashboardAccessMessage.textContent = "You must log in to continue.";
                }

                window.scrollTo({ top: 0, behavior: "smooth" });
            });
        });
    }

    if (requiresBankLinkItems.length && isDashboardAuthenticated) {
        requiresBankLinkItems.forEach(function(item) {
            item.addEventListener("click", function(event) {
                event.preventDefault();

                if (dashboardAccessMessage) {
                    dashboardAccessMessage.textContent = "You must link a bank account first.";
                }

                window.scrollTo({ top: 0, behavior: "smooth" });
            });
        });
    }

    if (scrollTargetItems.length && isDashboardAuthenticated) {
        scrollTargetItems.forEach(function(item) {
            item.addEventListener("click", function(event) {
                event.preventDefault();

                const targetId = item.dataset.scrollTarget;
                const target = targetId ? document.getElementById(targetId) : null;

                if (target) {
                    target.scrollIntoView({ behavior: "smooth", block: "start" });
                }
            });
        });
    }

    if (bankNavigationItems.length && isDashboardAuthenticated) {
        bankNavigationItems.forEach(function(item) {
            item.addEventListener("click", function() {
                const targetUrl = item.dataset.bankUrl;

                if (targetUrl) {
                    window.location.href = targetUrl;
                }
            });
        });
    }

    function setBankVerifyStatus(message, type) {
        if (!bankVerifyStatus) {
            return;
        }

        bankVerifyStatus.textContent = message;
        bankVerifyStatus.className = type ? `bank-verify-status ${type}` : "bank-verify-status";
    }

    if (sendBankOtpButton && bankVerifyEmail && bankVerifyShell) {
        sendBankOtpButton.addEventListener("click", function() {
            const email = bankVerifyEmail.value.trim();
            const bankSlug = bankVerifyShell.dataset.bankSlug || "";

            if (!email) {
                setBankVerifyStatus("Please enter your email address.", "error");
                return;
            }

            fetch("/dashboard/send-bank-verification-otp/", {
                method: "POST",
                headers: {
                    "Content-Type": "application/x-www-form-urlencoded",
                    "X-CSRFToken": getCSRFToken()
                },
                body: `email=${encodeURIComponent(email)}&bank_slug=${encodeURIComponent(bankSlug)}`
            })
                .then(function(res) {
                    return res.json();
                })
                .then(function(data) {
                    setBankVerifyStatus(data.message, data.status === "success" ? "success" : "error");
                })
                .catch(function() {
                    setBankVerifyStatus("Unable to send OTP. Please try again.", "error");
                });
        });
    }

    if (verifyBankOtpButton && bankVerifyOtp) {
        verifyBankOtpButton.addEventListener("click", function() {
            const otp = bankVerifyOtp.value.trim();

            if (!otp) {
                setBankVerifyStatus("Please enter the OTP.", "error");
                return;
            }

            fetch("/dashboard/verify-bank-verification-otp/", {
                method: "POST",
                headers: {
                    "Content-Type": "application/x-www-form-urlencoded",
                    "X-CSRFToken": getCSRFToken()
                },
                body: `otp=${encodeURIComponent(otp)}`
            })
                .then(function(res) {
                    return res.json();
                })
                .then(function(data) {
                    setBankVerifyStatus(data.message, data.status === "success" ? "success" : "error");

                    if (data.status === "success" && data.redirect_url) {
                        window.setTimeout(function() {
                            window.location.href = data.redirect_url;
                        }, 500);
                    }
                })
                .catch(function() {
                    setBankVerifyStatus("Unable to verify OTP. Please try again.", "error");
                });
        });
    }

    if (numericOnlyInputs.length) {
        numericOnlyInputs.forEach(function(input) {
            input.addEventListener("input", function() {
                input.value = input.value.replace(/\D/g, "");
            });
        });
    }

    if (expiryInputs.length) {
        expiryInputs.forEach(function(input) {
            input.addEventListener("input", function() {
                const digits = input.value.replace(/\D/g, "").slice(0, 4);

                if (digits.length <= 2) {
                    input.value = digits;
                } else {
                    input.value = digits.slice(0, 2) + "/" + digits.slice(2);
                }
            });
        });
    }

    if (balanceToggle && balancePanel) {
        balanceToggle.addEventListener("click", function() {
            const isOpen = balancePanel.classList.toggle("is-open");
            balanceToggle.classList.toggle("is-open", isOpen);
            balanceToggle.setAttribute("aria-expanded", isOpen ? "true" : "false");
        });
    }

    if (paymentToggle && paymentPanel) {
        paymentToggle.addEventListener("click", function() {
            paymentPanel.classList.add("is-open");
            paymentPanel.scrollIntoView({ behavior: "smooth", block: "nearest" });
        });
    }

    if (recentRequestContacts.length && requestRecipientInput) {
        recentRequestContacts.forEach(function(contact) {
            contact.addEventListener("click", function() {
                const identifier = contact.dataset.requestRecipient || "";
                const name = contact.dataset.requestName || "";

                requestRecipientInput.value = identifier;

                if (requestRecipientName) {
                    requestRecipientName.textContent = name;
                    requestRecipientName.classList.toggle("is-hidden", !name);
                }

                requestRecipientInput.focus();
            });
        });
    }

    if (overviewDataScript) {
        initializeDashboardOverview(overviewDataScript);
    }

    if (qrDownloadButton) {
        qrDownloadButton.addEventListener("click", function() {
            downloadQrImage(qrDownloadButton.dataset.qrImage, qrDownloadButton.dataset.qrFilename || "paynow-qr.png");
        });
    }

    if (qrShareButton) {
        qrShareButton.addEventListener("click", function() {
            shareQrImage(
                qrShareButton.dataset.qrImage,
                qrShareButton.dataset.qrFilename || "paynow-qr.png",
                qrShareButton.dataset.qrTitle || "PayNow QR Code"
            );
        });
    }
});

function getCSRFToken() {
    const cookieValue = document.cookie
        .split("; ")
        .find(function(row) {
            return row.startsWith("csrftoken=");
        });

    return cookieValue ? cookieValue.split("=")[1] : "";
}

function initializeDashboardOverview(dataScript) {
    const transactions = JSON.parse(dataScript.textContent || "[]");
    const searchInput = document.getElementById("dashboardOverviewSearch");
    const dateInput = document.getElementById("dashboardOverviewDate");
    const periodButtons = document.querySelectorAll("[data-overview-period]");
    const metricCount = document.getElementById("dashboardMetricCount");
    const metricValue = document.getElementById("dashboardMetricValue");
    const metricRate = document.getElementById("dashboardMetricRate");
    const metricAverage = document.getElementById("dashboardMetricAverage");
    const chartLine = document.getElementById("dashboardOverviewLine");
    const chartArea = document.getElementById("dashboardOverviewArea");
    const chartPoints = document.getElementById("dashboardOverviewPoints");
    const chartYAxis = document.getElementById("dashboardChartYAxis");
    const chartXAxis = document.getElementById("dashboardOverviewXAxis");
    const chartTotal = document.getElementById("dashboardChartTotal");
    const chartLegendPrimary = document.getElementById("dashboardChartLegendPrimary");
    const donut = document.getElementById("dashboardOverviewDonut");
    const donutSent = document.getElementById("dashboardDonutSent");
    const donutReceived = document.getElementById("dashboardDonutReceived");
    const donutValue = document.getElementById("dashboardDonutValue");
    const recentRows = document.getElementById("dashboardRecentRows");
    const recentSummary = document.getElementById("dashboardRecentSummary");
    const chartGrid = document.getElementById("dashboardChartGrid");

    if (!metricCount || !chartLine || !chartArea || !recentRows) {
        return;
    }

    const state = {
        period: "week",
        search: "",
        selectedDate: "",
    };
    const defaultAnchorDate = transactions.length
        ? new Date(transactions[0].date + "T00:00:00")
        : new Date();

    if (dateInput) {
        dateInput.value = "";
    }

    if (chartGrid && !chartGrid.children.length) {
        for (let index = 0; index < 5; index += 1) {
            const line = document.createElement("span");
            chartGrid.appendChild(line);
        }
    }

    if (chartYAxis) {
        chartYAxis.innerHTML = ["10k", "8k", "6k", "4k", "2k"].map(function(label) {
            return "<span>" + label + "</span>";
        }).join("");
    }

    if (searchInput) {
        searchInput.addEventListener("input", function() {
            state.search = searchInput.value.trim().toLowerCase();
            renderOverview();
        });
    }

    if (dateInput) {
        dateInput.addEventListener("input", function() {
            state.selectedDate = dateInput.value;
            renderOverview();
        });
    }

    periodButtons.forEach(function(button) {
        button.addEventListener("click", function() {
            state.period = button.dataset.overviewPeriod || "week";
            periodButtons.forEach(function(otherButton) {
                otherButton.classList.toggle("is-active", otherButton === button);
            });
            renderOverview();
        });
    });

    renderOverview();

    function renderOverview() {
        const searchFiltered = transactions.filter(function(transaction) {
            if (!state.search) {
                return true;
            }

            const haystack = [
                transaction.counterpart,
                transaction.note,
                transaction.direction,
                transaction.upi_id,
                transaction.status,
            ].join(" ").toLowerCase();

            return haystack.includes(state.search);
        });

        const listTransactions = state.selectedDate
            ? searchFiltered.filter(function(transaction) {
                return transaction.date === state.selectedDate;
            })
            : searchFiltered;

        renderMetrics(listTransactions);
        renderRecentTransactions(listTransactions);
        renderDonut(listTransactions);
        renderChart(searchFiltered);
    }

    function renderMetrics(items) {
        const totalCount = items.length;
        const totalValue = items.reduce(function(sum, item) {
            return sum + Math.abs(Number(item.signed_amount || item.amount || 0));
        }, 0);
        const avgValue = totalCount ? totalValue / totalCount : 0;
        const successRate = totalCount ? 100 : 0;

        metricCount.textContent = formatNumber(totalCount);
        metricValue.textContent = "Rs. " + formatAmount(totalValue);
        metricRate.textContent = successRate.toFixed(1).replace(".0", "") + "%";
        metricAverage.textContent = "Rs. " + formatAmount(avgValue);
    }

    function renderRecentTransactions(items) {
        recentRows.innerHTML = "";

        if (!items.length) {
            recentRows.innerHTML = '<div class="dashboard-recent-empty">No transactions found for the selected filters.</div>';
            recentSummary.textContent = state.selectedDate
                ? "Showing transactions for " + formatHumanDate(state.selectedDate) + "."
                : "No transactions match your current filter.";
            return;
        }

        const limitedItems = items.slice(0, 8);
        recentSummary.textContent = state.selectedDate
            ? "Showing transactions for " + formatHumanDate(state.selectedDate) + "."
            : "Showing your latest transaction activity.";

        limitedItems.forEach(function(item) {
            const row = document.createElement("div");
            row.className = "dashboard-recent-row";
            row.innerHTML =
                '<div class="dashboard-recent-party">' +
                    '<img src="/static/images/profile.jpg" alt="' + escapeHtml(item.counterpart) + '">' +
                    '<div><strong>' + escapeHtml(item.counterpart) + '</strong><span>' + escapeHtml(item.note) + '</span></div>' +
                '</div>' +
                '<div class="dashboard-recent-date">' +
                    '<strong>' + escapeHtml(item.display_date) + '</strong><span>' + escapeHtml(item.weekday) + " • " + escapeHtml(item.time) + '</span>' +
                '</div>' +
                '<div class="dashboard-recent-amount">' +
                    '<strong>' + (item.direction === "Sent" ? "-" : "+") + "Rs. " + formatAmount(Math.abs(Number(item.signed_amount))) + '</strong>' +
                    '<span>' + escapeHtml(item.flow_label) + '</span>' +
                '</div>' +
                '<div><span class="dashboard-recent-status">' + escapeHtml(item.status) + '</span></div>';
            recentRows.appendChild(row);
        });
    }

    function renderDonut(items) {
        const sentItems = items.filter(function(item) { return item.direction === "Sent"; });
        const receivedItems = items.filter(function(item) { return item.direction === "Received"; });
        const sentCount = sentItems.length;
        const receivedCount = receivedItems.length;
        const totalCount = sentCount + receivedCount;
        const sentAngle = totalCount ? (sentCount / totalCount) * 360 : 180;
        const totalValue = items.reduce(function(sum, item) {
            return sum + Math.abs(Number(item.signed_amount || 0));
        }, 0);

        donut.style.background = "conic-gradient(#3f7eed 0deg " + sentAngle + "deg, #22c55e " + sentAngle + "deg 360deg)";
        donutSent.textContent = sentCount + " txns";
        donutReceived.textContent = receivedCount + " txns";
        donutValue.textContent = "Rs. " + formatAmount(totalValue);
    }

    function renderChart(items) {
        const grouped = buildGroupedSeries(items, state.period, state.selectedDate, defaultAnchorDate);
        const maxValue = 10000;
        const width = 1000;
        const height = 280;
        const points = grouped.map(function(entry, index) {
            const x = grouped.length === 1 ? 20 : 20 + (index * (width - 40) / (grouped.length - 1));
            const scaledValue = Math.min(entry.value, maxValue);
            const y = height - ((scaledValue / maxValue) * (height - 20));
            return { x: x, y: y, label: entry.label, value: entry.value };
        });

        chartXAxis.innerHTML = grouped.map(function(entry) {
            return "<span>" + escapeHtml(entry.label) + "</span>";
        }).join("");

        if (!points.length) {
            chartLine.setAttribute("d", "");
            chartArea.setAttribute("d", "");
            chartPoints.innerHTML = "";
            chartLegendPrimary.textContent = "No chart data for the selected filters.";
            chartTotal.textContent = "Total : Rs. 0.00";
            return;
        }

        const linePath = points.map(function(point, index) {
            return (index === 0 ? "M" : "L") + point.x + "," + point.y;
        }).join(" ");
        const areaPath = linePath + " L" + points[points.length - 1].x + "," + height + " L" + points[0].x + "," + height + " Z";

        chartLine.setAttribute("d", linePath);
        chartArea.setAttribute("d", areaPath);
        chartPoints.innerHTML = points.map(function(point) {
            return '<span class="dashboard-chart-point" style="left:calc(' + ((point.x / width) * 100) + '% - 6px); top:calc(' + ((point.y / 320) * 100) + '% - 6px);" title="Rs. ' + formatAmount(point.value) + '"></span>';
        }).join("");
        chartLegendPrimary.textContent = "Transaction values grouped by " + state.period + ".";
        chartTotal.textContent = "Total : Rs. " + formatAmount(grouped.reduce(function(sum, item) { return sum + item.value; }, 0));
    }
}

function buildGroupedSeries(items, period, selectedDate, fallbackAnchorDate) {
    const anchorDate = selectedDate ? new Date(selectedDate + "T00:00:00") : fallbackAnchorDate;
    const map = new Map();
    const labels = [];

    if (period === "day") {
        const targetDate = selectedDate || formatLocalIsoDate(anchorDate);
        for (let hour = 0; hour < 24; hour += 4) {
            const label = String(hour).padStart(2, "0") + ":00";
            labels.push(label);
            map.set(label, 0);
        }

        items.forEach(function(item) {
            if (item.date !== targetDate) {
                return;
            }
            const hour = new Date(item.datetime).getHours();
            const slot = Math.floor(hour / 4) * 4;
            const label = String(slot).padStart(2, "0") + ":00";
            map.set(label, (map.get(label) || 0) + Math.abs(Number(item.signed_amount)));
        });
    } else if (period === "month") {
        const year = anchorDate.getFullYear();
        const month = anchorDate.getMonth();
        const weekLabels = ["Week 1", "Week 2", "Week 3", "Week 4", "Week 5"];
        weekLabels.forEach(function(label) {
            labels.push(label);
            map.set(label, 0);
        });

        items.forEach(function(item) {
            const date = new Date(item.date + "T00:00:00");
            if (date.getFullYear() !== year || date.getMonth() !== month) {
                return;
            }
            const bucket = "Week " + Math.min(5, Math.floor((date.getDate() - 1) / 7) + 1);
            map.set(bucket, (map.get(bucket) || 0) + Math.abs(Number(item.signed_amount)));
        });
    } else if (period === "year") {
        const year = anchorDate.getFullYear();
        for (let month = 0; month < 12; month += 1) {
            const label = new Date(year, month, 1).toLocaleString("en-US", { month: "short" });
            labels.push(label);
            map.set(label, 0);
        }

        items.forEach(function(item) {
            const date = new Date(item.date + "T00:00:00");
            if (date.getFullYear() !== year) {
                return;
            }
            const label = date.toLocaleString("en-US", { month: "short" });
            map.set(label, (map.get(label) || 0) + Math.abs(Number(item.signed_amount)));
        });
    } else {
        for (let offset = 6; offset >= 0; offset -= 1) {
            const date = new Date(anchorDate);
            date.setDate(anchorDate.getDate() - offset);
            const iso = formatLocalIsoDate(date);
            const label = date.toLocaleString("en-US", { weekday: "short" });
            labels.push(label);
            map.set(iso, { label: label, value: 0 });
        }

        items.forEach(function(item) {
            if (!map.has(item.date)) {
                return;
            }
            const bucket = map.get(item.date);
            bucket.value += Math.abs(Number(item.signed_amount));
        });

        return Array.from(map.values());
    }

    return labels.map(function(label) {
        return { label: label, value: map.get(label) || 0 };
    });
}

function formatAmount(value) {
    return Number(value || 0).toLocaleString("en-IN", {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
    });
}

function formatNumber(value) {
    return Number(value || 0).toLocaleString("en-IN");
}

function formatHumanDate(value) {
    const date = new Date(value + "T00:00:00");
    return date.toLocaleString("en-US", {
        month: "short",
        day: "numeric",
        year: "numeric",
    });
}

function escapeHtml(value) {
    return String(value || "")
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#39;");
}

function formatLocalIsoDate(date) {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, "0");
    const day = String(date.getDate()).padStart(2, "0");
    return year + "-" + month + "-" + day;
}

async function downloadQrImage(imageUrl, filename) {
    try {
        const blob = await fetchQrBlob(imageUrl);
        const objectUrl = URL.createObjectURL(blob);
        const link = document.createElement("a");
        link.href = objectUrl;
        link.download = filename;
        document.body.appendChild(link);
        link.click();
        link.remove();
        URL.revokeObjectURL(objectUrl);
    } catch (error) {
        window.alert("Unable to download the QR code right now.");
    }
}

async function shareQrImage(imageUrl, filename, title) {
    try {
        const blob = await fetchQrBlob(imageUrl);
        const file = new File([blob], filename, { type: blob.type || "image/png" });

        if (navigator.canShare && navigator.canShare({ files: [file] }) && navigator.share) {
            await navigator.share({
                title: title,
                files: [file],
            });
            return;
        }

        await downloadQrImage(imageUrl, filename);
    } catch (error) {
        window.alert("Unable to share the QR code right now.");
    }
}

async function fetchQrBlob(imageUrl) {
    const response = await fetch(imageUrl, { mode: "cors" });
    if (!response.ok) {
        throw new Error("QR fetch failed");
    }
    return response.blob();
}
