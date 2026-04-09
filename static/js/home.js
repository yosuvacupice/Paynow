// Register popup
function openRegister() {
    closeSignup();
    closeOtpPopup();
    document.getElementById("registerPopup").style.display = "block";
}

function closeRegister() {
    document.getElementById("registerPopup").style.display = "none";
}

// Signup popup
function openSignup() {
    closeRegister();
    closeOtpPopup();
    document.getElementById("signupPopup").style.display = "block";
}

function closeSignup() {
    document.getElementById("signupPopup").style.display = "none";
}

// Forgot password popup
function openOtpPopup(event, email) {
    if (event) {
        event.preventDefault();
    }

    const popup = document.getElementById("otpPopup");
    const status = document.getElementById("otpStatus");
    const emailInput = document.getElementById("otpEmail");
    const otpInput = document.getElementById("otpInput");

    if (status) {
        status.textContent = "";
        status.className = "otp-status";
    }

    if (emailInput && email) {
        emailInput.value = email;
    }

    if (otpInput) {
        otpInput.value = "";
    }

    popup.style.display = "block";
}

function closeOtpPopup() {
    const popup = document.getElementById("otpPopup");

    if (popup) {
        popup.style.display = "none";
    }
}

// Notification popup
function toggleNotification() {
    const box = document.getElementById("notificationBox");
    box.style.display = (box.style.display === "block") ? "none" : "block";
}

// Profile dropdown
function toggleProfile() {
    const box = document.getElementById("profileMenu");
    box.style.display = (box.style.display === "block") ? "none" : "block";
}

// Click outside close popup
window.addEventListener("click", function(event) {
    const registerPopup = document.getElementById("registerPopup");
    const signupPopup = document.getElementById("signupPopup");
    const otpPopup = document.getElementById("otpPopup");

    if (event.target === registerPopup) {
        closeRegister();
    }

    if (event.target === signupPopup) {
        closeSignup();
    }

    if (event.target === otpPopup) {
        closeOtpPopup();
    }
});

// Password show or hide toggle
document.querySelectorAll(".password-toggle").forEach(function(toggleButton) {
    toggleButton.addEventListener("click", function() {
        const passwordInput = this.parentElement.querySelector("input");
        const icon = this.querySelector("i");
        const isHidden = passwordInput.type === "password";

        passwordInput.type = isHidden ? "text" : "password";
        this.setAttribute("aria-label", isHidden ? "Hide password" : "Show password");
        icon.className = isHidden ? "ri-eye-off-line" : "ri-eye-line";
    });
});

// Auto open popup based on message
window.onload = function() {
    const messageBox = document.querySelector(".flash-message");

    if (messageBox) {
        const text = messageBox.innerText.toLowerCase();

        if (text.includes("success")) {
            document.getElementById("registerPopup").style.display = "block";
        } else if (
            text.includes("name") ||
            text.includes("gmail") ||
            text.includes("exists")
        ) {
            document.getElementById("signupPopup").style.display = "block";
        } else {
            document.getElementById("registerPopup").style.display = "block";
        }
    }
};

document.addEventListener("DOMContentLoaded", function() {
    const navItems = document.querySelectorAll("button.account-nav-item");
    const panels = document.querySelectorAll(".account-panel");
    const otpInputs = document.querySelectorAll("#otpInput, #bankVerifyOtp");

    navItems.forEach(function(item) {
        item.addEventListener("click", function() {
            const target = item.dataset.section;

            navItems.forEach(function(navItem) {
                navItem.classList.remove("is-active");
            });

            panels.forEach(function(panel) {
                panel.classList.toggle("is-active", panel.dataset.panel === target);
            });

            item.classList.add("is-active");
        });
    });

    if (document.querySelector("input[name='current_password'][readonly]")) {
        applyOtpVerificationState();
    }

    otpInputs.forEach(function(input) {
        input.addEventListener("input", function() {
            input.value = input.value.replace(/\D/g, "");
        });
    });
});

function setOtpStatus(message, type) {
    const status = document.getElementById("otpStatus");

    if (!status) {
        return;
    }

    status.textContent = message;
    status.className = type ? `otp-status ${type}` : "otp-status";
}

function applyOtpVerificationState() {
    const currentPasswordInput = document.querySelector("input[name='current_password']");

    if (!currentPasswordInput) {
        return;
    }

    currentPasswordInput.type = "text";
    currentPasswordInput.value = "OTP verified";
    currentPasswordInput.readOnly = true;
    currentPasswordInput.required = false;
}

function sendOtp() {
    const email = document.getElementById("otpEmail").value.trim();

    if (!email) {
        setOtpStatus("Please enter your email address.", "error");
        return;
    }

    fetch("/send-otp/", {
        method: "POST",
        headers: {
            "Content-Type": "application/x-www-form-urlencoded",
            "X-CSRFToken": getCSRFToken()
        },
        body: `email=${encodeURIComponent(email)}`
    })
        .then(function(res) {
            return res.json();
        })
        .then(function(data) {
            setOtpStatus(data.message, data.status === "success" ? "success" : "error");
        })
        .catch(function() {
            setOtpStatus("Unable to send OTP. Please try again in a moment.", "error");
        });
}

function verifyOtp() {
    const otp = document.getElementById("otpInput").value.trim();

    if (!otp) {
        setOtpStatus("Please enter the OTP.", "error");
        return;
    }

    fetch("/verify-otp/", {
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
            setOtpStatus(data.message, data.status === "success" ? "success" : "error");

            if (data.status === "success") {
                applyOtpVerificationState();
                if (data.redirect_url) {
                    window.location.href = data.redirect_url;
                }
            }
        })
        .catch(function() {
            setOtpStatus("Unable to verify OTP. Please try again.", "error");
        });
}

function getCSRFToken() {
    const csrfInput = document.querySelector("[name=csrfmiddlewaretoken]");
    return csrfInput ? csrfInput.value : "";
}
