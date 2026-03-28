package com.example.demo.marketplace.v1.error;

import jakarta.servlet.http.HttpServletRequest;
import java.util.UUID;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;

@RestControllerAdvice
public class GlobalApiExceptionHandler {

    @ExceptionHandler(ApiException.class)
    public ResponseEntity<ApiErrorResponse> handleApiException(ApiException ex, HttpServletRequest request) {
        return ResponseEntity.status(ex.getStatus()).body(new ApiErrorResponse(ex.getCode(), ex.getMessage(), requestId(request)));
    }

    @ExceptionHandler(MethodArgumentNotValidException.class)
    public ResponseEntity<ApiErrorResponse> handleValidation(MethodArgumentNotValidException ex, HttpServletRequest request) {
        return ResponseEntity.badRequest().body(new ApiErrorResponse("VALIDATION_ERROR", "Request validation failed", requestId(request)));
    }

    @ExceptionHandler(Exception.class)
    public ResponseEntity<ApiErrorResponse> handleUnexpected(Exception ex, HttpServletRequest request) {
        return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
            .body(new ApiErrorResponse("INTERNAL_SERVER_ERROR", "Unexpected server error", requestId(request)));
    }

    private String requestId(HttpServletRequest request) {
        String header = request.getHeader("X-Request-Id");
        return (header == null || header.isBlank()) ? UUID.randomUUID().toString() : header;
    }
}
