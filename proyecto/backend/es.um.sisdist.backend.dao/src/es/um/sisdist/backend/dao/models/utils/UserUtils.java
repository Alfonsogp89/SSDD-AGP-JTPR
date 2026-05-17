package es.um.sisdist.backend.dao.models.utils;

import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.nio.charset.StandardCharsets;

public class UserUtils
{
    private static final String PEPPER = "ssdd-secret";

    private static String bytesToHex(byte[] bytes)
    {
        StringBuilder sb = new StringBuilder();
        for (byte b : bytes)
            sb.append(String.format("%02x", b));
        return sb.toString();
    }

    public static String hashPassword(String clearpass)
    {
        try
        {
            String salted = PEPPER + ":" + clearpass;
            MessageDigest sha = MessageDigest.getInstance("SHA-256");
            return bytesToHex(sha.digest(salted.getBytes(StandardCharsets.UTF_8)));
        }
        catch (NoSuchAlgorithmException e)
        {
            throw new RuntimeException("SHA-256 not available", e);
        }
    }
}
