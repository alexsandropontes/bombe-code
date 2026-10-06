package com.codeforge.snippets.validation;

public final class CnpjValidator {
    private static final int[] PESO1 = {5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2};
    private static final int[] PESO2 = {6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2};

    private CnpjValidator() {}

    public static boolean validar(String cnpj) {
        if (cnpj == null || cnpj.isBlank()) return false;
        String clean = cnpj.replaceAll("\\D", "");
        if (clean.length() != 14) return false;
        if (clean.matches("(\\d)\\1{13}")) return false;

        try {
            int sm = 0;
            for (int i = 0; i < 12; i++) sm += (clean.charAt(i) - '0') * PESO1[i];
            int r = sm % 11;
            char dig13 = (r < 2) ? '0' : (char) ((11 - r) + '0');

            sm = 0;
            for (int i = 0; i < 13; i++) sm += (clean.charAt(i) - '0') * PESO2[i];
            r = sm % 11;
            char dig14 = (r < 2) ? '0' : (char) ((11 - r) + '0');

            return dig13 == clean.charAt(12) && dig14 == clean.charAt(13);
        } catch (Exception e) {
            return false;
        }
    }
}
