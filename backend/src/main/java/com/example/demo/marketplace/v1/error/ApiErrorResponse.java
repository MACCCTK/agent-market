package com.example.demo.marketplace.v1.error;

public record ApiErrorResponse(String code, String message, String requestId) {
}
