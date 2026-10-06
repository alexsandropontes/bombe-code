package com.codeforge.snippets.validation;

import java.util.regex.Pattern;

public final class CpfValidator {
    private static final Pattern NON_DIGIT = Pattern.compile("\\D");

    private CpfValidator() {}

    public static boolean validar(String cpf) {
        if (cpf == null || cpf.isBlank()) return false;
        String clean = NON_DIGIT.matcher(cpf).replaceAll("");
        if (clean.length() != 11) return false;
        if (clean.matches("(\\d)\\1{10}")) return false;

        try {
            int sm = 0;
            for (int i = 0; i < 9; i++) {
                int num = clean.charAt(i) - '0';
                sm += num * (10 - i);
            }
            int r = 11 - (sm % 11);
            char dig10 = (r == 10 || r == 11) ? '0' : (char) (r + '0');

            sm = 0;
            for (int i = 0; i < 10; i++) {
                int num = clean.charAt(i) - '0';
                sm += num * (11 - i);
            }
            r = 11 - (sm % 11);
            char dig11 = (r == 10 || r == 11) ? '0' : (char) (r + '0');

            return dig10 == clean.charAt(9) && dig11 == clean.charAt(10);
        } catch (Exception e) {
            return false;
        }
    }

    public static String formatar(String cpf) {
        if (cpf == null || cpf.isBlank()) return "";
        String clean = NON_DIGIT.matcher(cpf).replaceAll("");
        if (clean.length() != 11) return cpf;
        return clean.replaceAll("(\\d{3})(\\d{3})(\\d{3})(\\d{2})", "$1.$2.$3-$4");
    }
}
